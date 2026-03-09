"""
Checkpoint Handler — Business logic for checkpoint history and thread turn operations.

Provides endpoints for:
- Listing turn-boundary checkpoints (for edit/regenerate/retry)
- Retrying failed/interrupted threads from the appropriate checkpoint
"""

import logging

from fastapi import HTTPException

from src.server.utils.checkpoint_helpers import (
    build_checkpoint_config,
    get_checkpointer,
)
from src.server.models.workflow import (
    TurnCheckpointInfo,
    ThreadTurnsResponse,
)

logger = logging.getLogger(__name__)


async def get_thread_turns(
    thread_id: str, branch_tip_checkpoint_id: str | None = None
) -> ThreadTurnsResponse:
    """
    Scan checkpoints for a thread and identify turn boundaries on the current branch.

    Edit/regenerate operations create forks in the checkpoint graph — new branches
    that share a parent with the old branch. To avoid counting stale forks as turns,
    we walk the parent chain from the branch tip and only count ``source=input``
    checkpoints that are ancestors of the current state.

    Args:
        thread_id: Thread identifier
        branch_tip_checkpoint_id: Optional stored checkpoint ID to use as branch tip.
            Falls back to newest checkpoint (alist[0]) if not provided or not found.

    Returns:
        ThreadTurnsResponse with per-turn checkpoint info and retry checkpoint ID
    """
    checkpointer = get_checkpointer()
    config = build_checkpoint_config(thread_id)

    # Collect all checkpoints (alist returns newest first)
    checkpoints = []
    try:
        async for cp_tuple in checkpointer.alist(config):
            checkpoints.append(cp_tuple)
    except Exception as e:
        logger.error(f"[CHECKPOINT] Failed to list checkpoints for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve checkpoint history")

    if not checkpoints:
        return ThreadTurnsResponse(
            thread_id=thread_id,
            turns=[],
            retry_checkpoint_id=None,
        )

    # Build lookup: checkpoint_id -> cp_tuple
    cp_by_id = {}
    for cp in checkpoints:
        cp_id = cp.config["configurable"]["checkpoint_id"]
        cp_by_id[cp_id] = cp

    # Determine branch tip: prefer stored checkpoint_id, fall back to newest.
    if branch_tip_checkpoint_id and branch_tip_checkpoint_id in cp_by_id:
        latest = cp_by_id[branch_tip_checkpoint_id]
    else:
        latest = checkpoints[0]
    current_branch: set[str] = set()
    current_id: str | None = latest.config["configurable"]["checkpoint_id"]
    while current_id and current_id in cp_by_id:
        current_branch.add(current_id)
        cp = cp_by_id[current_id]
        current_id = (
            cp.parent_config["configurable"].get("checkpoint_id")
            if cp.parent_config
            else None
        )

    # Collect turns: source=input checkpoints (user messages) and HITL resume
    # boundaries (__resume__ in pending_writes) on the current branch,
    # processed in chronological order (reverse of alist).
    turns = []
    for cp_tuple in reversed(checkpoints):
        cp_id = cp_tuple.config["configurable"]["checkpoint_id"]
        if cp_id not in current_branch:
            continue
        metadata = cp_tuple.metadata or {}
        is_source_input = metadata.get("source") == "input"

        # Detect HITL resume: checkpoint has __resume__ in pending_writes.
        # Command(resume=...) creates source=loop (not source=input), so
        # we detect these by looking for the __resume__ channel.
        is_hitl_resume = False
        if not is_source_input and cp_tuple.pending_writes:
            is_hitl_resume = any(
                channel == "__resume__"
                for _, channel, _ in cp_tuple.pending_writes
            )

        if is_source_input or is_hitl_resume:
            # The parent checkpoint is the state BEFORE this turn
            edit_checkpoint_id = None
            if is_source_input and cp_tuple.parent_config:
                edit_checkpoint_id = cp_tuple.parent_config["configurable"].get("checkpoint_id")

            turns.append(TurnCheckpointInfo(
                turn_index=len(turns),
                edit_checkpoint_id=edit_checkpoint_id,
                regenerate_checkpoint_id=cp_id,
            ))

    retry_checkpoint_id = latest.config["configurable"]["checkpoint_id"]

    return ThreadTurnsResponse(
        thread_id=thread_id,
        turns=turns,
        retry_checkpoint_id=retry_checkpoint_id,
    )


async def get_retry_checkpoint(thread_id: str, checkpoint_id: str | None = None) -> str:
    """
    Determine the appropriate checkpoint ID for retrying a failed/interrupted thread.

    If checkpoint_id is provided, validates it exists and returns it.
    Otherwise, auto-detects the latest checkpoint.

    Args:
        thread_id: Thread identifier
        checkpoint_id: Optional explicit checkpoint ID

    Returns:
        The checkpoint ID to retry from

    Raises:
        HTTPException: If no checkpoint is found
    """
    checkpointer = get_checkpointer()

    if checkpoint_id:
        # Validate the provided checkpoint exists
        config = build_checkpoint_config(thread_id, checkpoint_id)
        cp_tuple = await checkpointer.aget_tuple(config)
        if not cp_tuple:
            raise HTTPException(
                status_code=404,
                detail=f"Checkpoint {checkpoint_id} not found for thread {thread_id}",
            )
        return checkpoint_id

    # Auto-detect: get the latest checkpoint
    config = build_checkpoint_config(thread_id)
    cp_tuple = await checkpointer.aget_tuple(config)
    if not cp_tuple:
        raise HTTPException(
            status_code=404,
            detail=f"No checkpoints found for thread {thread_id}",
        )

    return cp_tuple.config["configurable"]["checkpoint_id"]
