"""
Factor miner core implementations.

Provides async functions for managing alpha factors in the factor_library
table and experience memory in Redis.
"""

import copy
import logging
from datetime import datetime, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Json

from src.server.database.conversation import get_db_connection
from src.utils.cache.redis_cache import get_cache_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MEMORY: dict[str, Any] = {
    "version": 1,
    "library_size": 0,
    "last_updated": None,
    "recommended": [],
    "forbidden": [],
    "insights": [],
    "recent_logs": [],
}

_RECOMMENDED_MAX = 10
_FORBIDDEN_MAX = 15
_INSIGHTS_MAX = 15
_RECENT_LOGS_MAX = 20

_MEMORY_TTL = 7 * 86400  # 7 days


class CacheKeyBuilder:
    """Helper for building Redis keys with a namespace prefix."""

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace

    def build(self, *parts: str, params: dict[str, str] | None = None) -> str:
        """Build a colon-separated key: ``namespace:part1:part2:...``.

        If *params* is provided, the values are appended in sorted-key order.
        """
        segments = [self.namespace, *parts]
        if params:
            for k in sorted(params):
                segments.append(str(params[k]))
        return ":".join(segments)


_cache_key = CacheKeyBuilder("factor_miner")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_EVAL_CONFIG_REQUIRED_KEYS = {"universe", "symbols", "start_date", "end_date", "forward_return_days"}


def _validate_evaluation_config(evaluation_config: dict) -> None:
    """Raise ValueError if evaluation_config is missing required fields."""
    if not isinstance(evaluation_config, dict) or not evaluation_config:
        raise ValueError("evaluation_config must be a non-empty dict")

    has_required = bool(_EVAL_CONFIG_REQUIRED_KEYS & set(evaluation_config.keys()))
    if not has_required:
        raise ValueError(
            f"evaluation_config must contain at least one of: "
            f"{sorted(_EVAL_CONFIG_REQUIRED_KEYS)}"
        )


# ---------------------------------------------------------------------------
# admit_factor
# ---------------------------------------------------------------------------


async def admit_factor_impl(
    workspace_id: str,
    name: str,
    formula: str,
    category: str | None,
    ic_mean: float,
    icir: float | None,
    max_corr: float | None,
    evaluation_config: dict,
    parameters: dict | None,
) -> dict[str, Any]:
    """Insert or update a factor in the factor_library table.

    Uses ``ON CONFLICT`` on the ``(workspace_id, formula)`` unique constraint
    so that re-admitting the same formula updates metrics in-place.

    Returns a dict with ``message`` and the persisted row.
    """
    _validate_evaluation_config(evaluation_config)

    params = parameters or {}

    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO factor_library (
                    workspace_id, name, formula, category,
                    ic_mean, icir, max_corr,
                    evaluation_config, parameters,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (workspace_id, formula)
                DO UPDATE SET
                    name         = EXCLUDED.name,
                    category     = EXCLUDED.category,
                    ic_mean      = EXCLUDED.ic_mean,
                    icir         = EXCLUDED.icir,
                    max_corr     = EXCLUDED.max_corr,
                    evaluation_config = EXCLUDED.evaluation_config,
                    parameters   = EXCLUDED.parameters,
                    updated_at   = NOW()
                RETURNING id, workspace_id, name, formula, category,
                          ic_mean, icir, max_corr,
                          evaluation_config, parameters,
                          created_at, updated_at
                """,
                (
                    workspace_id,
                    name,
                    formula,
                    category,
                    ic_mean,
                    icir,
                    max_corr,
                    Json(evaluation_config),
                    Json(params),
                ),
            )
            row = await cur.fetchone()

    result = dict(row) if row else {}
    result["message"] = (
        f"Factor '{name}' admitted successfully"
        if row
        else "Failed to admit factor"
    )
    return result


# ---------------------------------------------------------------------------
# list_factors
# ---------------------------------------------------------------------------


async def list_factors_impl(workspace_id: str) -> dict[str, Any]:
    """Return all factors for a workspace as a structured list."""
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, workspace_id, name, formula, category,
                       ic_mean, icir, max_corr,
                       evaluation_config, parameters,
                       created_at, updated_at
                FROM factor_library
                WHERE workspace_id = %s
                ORDER BY created_at ASC
                """,
                (workspace_id,),
            )
            rows = await cur.fetchall()

    factors = [dict(r) for r in rows]
    return {"factors": factors, "count": len(factors)}


# ---------------------------------------------------------------------------
# get_factor_memory
# ---------------------------------------------------------------------------


async def get_factor_memory_impl(workspace_id: str) -> dict[str, Any]:
    """Read experience memory from Redis, returning DEFAULT_MEMORY if absent."""
    cache = get_cache_client()
    key = _cache_key.build("memory", params={"workspace_id": workspace_id})

    data = await cache.get(key)
    if data is None:
        return copy.deepcopy(DEFAULT_MEMORY)

    # Ensure all expected fields exist (forward-compatible with schema changes)
    result = copy.deepcopy(DEFAULT_MEMORY)
    result.update(data)
    return result


# ---------------------------------------------------------------------------
# update_factor_memory
# ---------------------------------------------------------------------------


async def update_factor_memory_impl(
    workspace_id: str,
    memory_patch: dict[str, Any],
) -> dict[str, Any]:
    """Merge *memory_patch* into the current experience memory and persist.

    .. note::

        **Concurrency limitation (MVP):** This implementation performs a
        non-atomic read-merge-write.  Under concurrent calls the last writer
        wins and intermediate patches may be silently dropped.  For the MVP
        this is acceptable because factor-miner runs as a single agent stream
        per workspace.  If concurrency becomes a concern, replace with a Redis
        Lua script or a WATCH/MULTI/EXEC transaction.
    """
    current = await get_factor_memory_impl(workspace_id)

    # --- Merge recommended (deduplicate by ``pattern``) ---
    if "recommended" in memory_patch:
        existing_patterns = {
            r.get("pattern") for r in current.get("recommended", []) if r.get("pattern")
        }
        for item in memory_patch["recommended"]:
            if isinstance(item, dict) and item.get("pattern") not in existing_patterns:
                current.setdefault("recommended", []).append(item)
                existing_patterns.add(item.get("pattern"))
        current["recommended"] = current["recommended"][-_RECOMMENDED_MAX:]

    # --- Merge forbidden (deduplicate by ``direction``) ---
    if "forbidden" in memory_patch:
        existing_directions = {
            f.get("direction") for f in current.get("forbidden", []) if f.get("direction")
        }
        for item in memory_patch["forbidden"]:
            if isinstance(item, dict) and item.get("direction") not in existing_directions:
                current.setdefault("forbidden", []).append(item)
                existing_directions.add(item.get("direction"))
        current["forbidden"] = current["forbidden"][-_FORBIDDEN_MAX:]

    # --- Merge insights (append, trim) ---
    if "insights" in memory_patch:
        new_insights = [s for s in memory_patch["insights"] if isinstance(s, str)]
        current.setdefault("insights", []).extend(new_insights)
        current["insights"] = current["insights"][-_INSIGHTS_MAX:]

    # --- Merge recent_logs (append, trim) ---
    if "recent_logs" in memory_patch:
        new_logs = [l for l in memory_patch["recent_logs"] if isinstance(l, dict)]
        current.setdefault("recent_logs", []).extend(new_logs)
        current["recent_logs"] = current["recent_logs"][-_RECENT_LOGS_MAX:]

    current["last_updated"] = datetime.now(timezone.utc).isoformat()
    if "library_size" in memory_patch:
        current["library_size"] = memory_patch["library_size"]

    # Persist
    cache = get_cache_client()
    key = _cache_key.build("memory", params={"workspace_id": workspace_id})
    await cache.set(key, current, ttl=_MEMORY_TTL)

    return {
        "message": "Experience memory updated",
        "memory": current,
    }
