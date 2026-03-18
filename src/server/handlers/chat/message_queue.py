"""Redis message queuing utilities for chat workflows.

Handles queuing, draining, and backfilling of user messages that arrive while
a workflow is already running. Messages are stored in Redis and consumed by
MessageQueueMiddleware (main agent) or SubagentMessageQueueMiddleware (subagents).
"""

import json
import time
from uuid import uuid4

from fastapi import HTTPException

from src.server.services.background_registry_store import BackgroundRegistryStore

from ._common import logger


async def backfill_queued_queries(
    thread_id: str, queued_messages: list[dict]
) -> None:
    """Backfill query records for queued messages that produced orphan responses.

    After a workflow completes, responses may exist at turn indices that have no
    matching query (because the user message was injected mid-workflow via
    MessageQueueMiddleware rather than arriving as a normal HTTP request).
    This function finds those orphan response turns and creates query records.
    """
    if not queued_messages:
        return

    from src.server.database.conversation import (
        create_query,
        get_queries_for_thread,
        get_responses_for_thread,
    )

    try:
        queries = await get_queries_for_thread(thread_id)
        responses = await get_responses_for_thread(thread_id)

        query_turns = {q["turn_index"] for q in queries}
        response_turns = {r["turn_index"] for r in responses}
        orphan_turns = sorted(response_turns - query_turns)

        if not orphan_turns:
            return

        # Match orphan turns with queued messages (FIFO order)
        for turn_index, msg in zip(orphan_turns, queued_messages):
            content = msg.get("content", "")
            if not content:
                continue
            await create_query(
                conversation_query_id=str(uuid4()),
                conversation_thread_id=thread_id,
                turn_index=turn_index,
                content=content,
                query_type="queued",
            )
            logger.info(
                f"[CHAT] Backfilled queued query: thread_id={thread_id} "
                f"turn_index={turn_index}"
            )
    except Exception as e:
        logger.error(f"[CHAT] Failed to backfill queued queries: {e}")


async def drain_queued_return_event(thread_id: str) -> str | None:
    """Drain unconsumed queued messages and format as a ``queued_message_returned`` SSE event.

    Returns the SSE string ready to yield, or ``None`` if no messages were queued.
    """
    unconsumed = await drain_queued_messages(thread_id)
    if not unconsumed:
        return None
    event_data = json.dumps({
        "thread_id": thread_id,
        "messages": [
            {"content": m["content"], "user_id": m.get("user_id")}
            for m in unconsumed
        ],
    })
    return f"event: queued_message_returned\ndata: {event_data}\n\n"


async def drain_queued_messages(thread_id: str) -> list[dict] | None:
    """Drain any unconsumed queued messages from Redis after workflow completion.

    Returns the messages so they can be sent back to the client for input restoration.
    """
    from src.utils.cache.redis_cache import get_cache_client

    cache = get_cache_client()
    if not cache.enabled or not cache.client:
        return None

    try:
        key = f"workflow:queued_messages:{thread_id}"
        pipe = cache.client.pipeline()
        pipe.lrange(key, 0, -1)
        pipe.delete(key)
        results = await pipe.execute()

        raw_messages = results[0]
        if not raw_messages:
            return None

        messages = []
        for raw in raw_messages:
            try:
                data = json.loads(
                    raw.decode("utf-8") if isinstance(raw, bytes) else raw
                )
                messages.append(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        return messages or None
    except Exception as e:
        logger.error(f"[CHAT] Failed to drain queued messages: {e}")
        return None


async def queue_message_for_thread(
    thread_id: str, content: str, user_id: str
) -> dict | None:
    """Queue a user message for injection into a running workflow via Redis.

    The MessageQueueMiddleware will pick these up before the next LLM call.

    Args:
        thread_id: The thread with an active workflow
        content: The user's message text
        user_id: User identifier

    Returns:
        Dict with queue position if successful, None if queuing failed
    """
    from src.utils.cache.redis_cache import get_cache_client

    cache = get_cache_client()
    if not cache.enabled or not cache.client:
        return None

    try:
        key = f"workflow:queued_messages:{thread_id}"
        message = json.dumps(
            {"content": content, "user_id": user_id, "timestamp": time.time()}
        )
        pipe = cache.client.pipeline()
        pipe.rpush(key, message)
        pipe.llen(key)
        pipe.expire(key, 3600)  # 1h TTL
        results = await pipe.execute()
        position = results[1]
        logger.info(
            f"[CHAT] Queued message for running workflow: "
            f"thread_id={thread_id} position={position}"
        )
        return {"position": position}
    except Exception as e:
        logger.error(f"[CHAT] Failed to queue message: {e}")
        return None


async def queue_message_for_subagent(
    thread_id: str,
    task_id: str,
    content: str,
    user_id: str,
) -> dict:
    """Queue a user message for injection into a running subagent via Redis.

    The SubagentMessageQueueMiddleware will pick these up before the subagent's next LLM call.

    Args:
        thread_id: The thread with an active workflow
        task_id: The subagent task ID (e.g., 'k7Xm2p')
        content: The message text to send
        user_id: User identifier

    Returns:
        Dict with success status and queue position
    """
    from src.utils.cache.redis_cache import get_cache_client

    # 1. Look up the registry for this thread
    registry_store = BackgroundRegistryStore.get_instance()
    registry = await registry_store.get_registry(thread_id)
    if registry is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active workflow for thread {thread_id}",
        )

    # 2. Look up the task by ID
    task = await registry.get_by_task_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task-{task_id} not found in thread {thread_id}",
        )

    # 3. Reject if already completed or cancelled
    if task.completed or task.cancelled:
        status = "cancelled" if task.cancelled else "completed"
        raise HTTPException(
            status_code=409,
            detail=f"Task-{task_id} has already {status}",
        )

    # 4. Queue to Redis (same pattern as _queue_followup_to_redis)
    cache = get_cache_client()
    if not cache.enabled or not cache.client:
        raise HTTPException(
            status_code=503,
            detail="Message queuing unavailable (Redis not connected)",
        )

    try:
        key = f"subagent:queued_messages:{task.tool_call_id}"
        payload = json.dumps(content)
        pipe = cache.client.pipeline()
        pipe.rpush(key, payload)
        pipe.llen(key)
        pipe.expire(key, 3600)  # 1h TTL
        results = await pipe.execute()
        position = results[1]

        logger.info(
            f"[SUBAGENT_MSG] Queued message for subagent: "
            f"thread_id={thread_id} task={task.display_id} position={position}"
        )
        return {
            "success": True,
            "tool_call_id": task.tool_call_id,
            "display_id": task.display_id,
            "queue_position": position,
        }
    except Exception as e:
        logger.error(f"[SUBAGENT_MSG] Failed to queue message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue message: {e}",
        )
