"""Unit tests for factor_miner host tool implementations."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from src.tools.factor_miner.implementations import (
    DEFAULT_MEMORY,
    _RECOMMENDED_MAX,
    admit_factor_impl,
    get_factor_memory_impl,
    list_factors_impl,
    update_factor_memory_impl,
)

_MOD = "src.tools.factor_miner.implementations"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_cursor():
    """AsyncMock cursor with execute/fetchone/fetchall."""
    cursor = AsyncMock()
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.fetchall = AsyncMock(return_value=[])
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    """AsyncMock connection that yields mock_cursor via cursor() context manager."""
    conn = AsyncMock()

    @asynccontextmanager
    async def _cursor_cm(**_kwargs):
        yield mock_cursor

    conn.cursor = _cursor_cm
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def mock_db_connection(mock_connection):
    """Patch get_db_connection to yield mock_connection."""

    @asynccontextmanager
    async def _fake_get_db_connection():
        yield mock_connection

    with patch(
        f"{_MOD}.get_db_connection",
        new=_fake_get_db_connection,
    ):
        yield mock_connection


@pytest.fixture
def mock_cache_client():
    """AsyncMock Redis cache client with get/set."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    return client


@pytest.fixture
def patch_cache_client(mock_cache_client):
    """Patch get_cache_client to return mock_cache_client."""
    with patch(f"{_MOD}.get_cache_client", return_value=mock_cache_client):
        yield mock_cache_client


# ---------------------------------------------------------------------------
# Canned data
# ---------------------------------------------------------------------------


def _make_factor_row(**overrides):
    """Build a canned factor_library row dict."""
    row = {
        "id": 1,
        "workspace_id": "ws-001",
        "name": "test_factor",
        "formula": "rank(close) / rank(volume)",
        "category": "momentum",
        "ic_mean": 0.05,
        "icir": 1.2,
        "max_corr": 0.3,
        "evaluation_config": {
            "universe": "csi500",
            "symbols": ["000001.SZ"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "forward_return_days": 5,
        },
        "parameters": {},
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# admit_factor tests
# ---------------------------------------------------------------------------


class TestAdmitFactor:
    @pytest.mark.asyncio
    async def test_admit_factor_success(self, mock_db_connection, mock_cursor):
        """Successful insert returns message and factor data."""
        row = _make_factor_row()
        mock_cursor.fetchone.return_value = row

        result = await admit_factor_impl(
            workspace_id="ws-001",
            name="test_factor",
            formula="rank(close) / rank(volume)",
            category="momentum",
            ic_mean=0.05,
            icir=1.2,
            max_corr=0.3,
            evaluation_config={
                "universe": "csi500",
                "symbols": ["000001.SZ"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "forward_return_days": 5,
            },
            parameters=None,
        )

        # Verify SQL was executed with INSERT
        mock_cursor.execute.assert_called_once()
        sql_arg = mock_cursor.execute.call_args[0][0]
        assert "INSERT" in sql_arg

        # Verify return shape
        assert result["message"] == "Factor 'test_factor' admitted successfully"
        assert result["name"] == "test_factor"
        assert result["workspace_id"] == "ws-001"

    @pytest.mark.asyncio
    async def test_admit_factor_rejects_empty_evaluation_config(self, mock_db_connection):
        """Empty evaluation_config raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            await admit_factor_impl(
                workspace_id="ws-001",
                name="bad_factor",
                formula="close",
                category=None,
                ic_mean=0.01,
                icir=None,
                max_corr=None,
                evaluation_config={},
                parameters=None,
            )

    @pytest.mark.asyncio
    async def test_admit_factor_rejects_invalid_evaluation_config(self, mock_db_connection):
        """evaluation_config without any required key raises ValueError."""
        with pytest.raises(ValueError, match="at least one of"):
            await admit_factor_impl(
                workspace_id="ws-001",
                name="bad_factor",
                formula="close",
                category=None,
                ic_mean=0.01,
                icir=None,
                max_corr=None,
                evaluation_config={"foo": "bar"},
                parameters=None,
            )


# ---------------------------------------------------------------------------
# list_factors tests
# ---------------------------------------------------------------------------


class TestListFactors:
    @pytest.mark.asyncio
    async def test_list_factors_returns_structured_data(self, mock_db_connection, mock_cursor):
        """Returns {factors: [...], count: N} with evaluation_config in each."""
        rows = [
            _make_factor_row(id=1, name="alpha_1"),
            _make_factor_row(id=2, name="alpha_2"),
        ]
        mock_cursor.fetchall.return_value = rows

        result = await list_factors_impl("ws-001")

        assert result["count"] == 2
        assert len(result["factors"]) == 2
        for factor in result["factors"]:
            assert "evaluation_config" in factor

    @pytest.mark.asyncio
    async def test_list_factors_empty(self, mock_db_connection, mock_cursor):
        """Empty workspace returns empty list with count 0."""
        mock_cursor.fetchall.return_value = []

        result = await list_factors_impl("ws-empty")

        assert result == {"factors": [], "count": 0}


# ---------------------------------------------------------------------------
# get_factor_memory tests
# ---------------------------------------------------------------------------


class TestGetFactorMemory:
    @pytest.mark.asyncio
    async def test_get_factor_memory_returns_default_when_absent(self, patch_cache_client):
        """Missing Redis key returns DEFAULT_MEMORY structure."""
        patch_cache_client.get.return_value = None

        result = await get_factor_memory_impl("ws-001")

        assert result == DEFAULT_MEMORY
        assert result["version"] == 1
        assert result["recommended"] == []
        assert result["forbidden"] == []

    @pytest.mark.asyncio
    async def test_get_factor_memory_returns_existing(self, patch_cache_client):
        """Existing Redis data is returned merged over DEFAULT_MEMORY."""
        stored = {
            "version": 1,
            "library_size": 5,
            "recommended": [{"pattern": "momentum"}],
            "forbidden": [{"direction": "short-biased"}],
        }
        patch_cache_client.get.return_value = stored

        result = await get_factor_memory_impl("ws-001")

        # Should merge DEFAULT_MEMORY with stored data
        assert result["library_size"] == 5
        assert result["recommended"] == [{"pattern": "momentum"}]
        assert result["forbidden"] == [{"direction": "short-biased"}]
        # DEFAULT_MEMORY fields present as fallback
        assert result["insights"] == []
        assert result["recent_logs"] == []


# ---------------------------------------------------------------------------
# update_factor_memory tests
# ---------------------------------------------------------------------------


class TestUpdateFactorMemory:
    @pytest.mark.asyncio
    async def test_update_factor_memory_merges_and_trims(self, patch_cache_client):
        """Recommended list is trimmed to _RECOMMENDED_MAX."""
        patch_cache_client.get.return_value = None  # start with empty memory

        # Build a patch with more than _RECOMMENDED_MAX items
        recommended = [
            {"pattern": f"pattern_{i}"} for i in range(_RECOMMENDED_MAX + 5)
        ]
        memory_patch = {"recommended": recommended}

        result = await update_factor_memory_impl("ws-001", memory_patch)

        mem = result["memory"]
        assert len(mem["recommended"]) == _RECOMMENDED_MAX
        # Should keep the LAST _RECOMMENDED_MAX items
        assert mem["recommended"][0]["pattern"] == "pattern_5"

    @pytest.mark.asyncio
    async def test_update_factor_memory_deduplicates_recommended(self, patch_cache_client):
        """Duplicate recommended patterns are merged (only one copy kept)."""
        existing = {
            "version": 1,
            "recommended": [{"pattern": "momentum_rank"}],
            "forbidden": [],
            "insights": [],
            "recent_logs": [],
        }
        patch_cache_client.get.return_value = existing

        memory_patch = {
            "recommended": [
                {"pattern": "momentum_rank"},  # duplicate
                {"pattern": "value_rank"},     # new
            ],
        }

        result = await update_factor_memory_impl("ws-001", memory_patch)

        patterns = [r["pattern"] for r in result["memory"]["recommended"]]
        assert patterns.count("momentum_rank") == 1
        assert "value_rank" in patterns

    @pytest.mark.asyncio
    async def test_update_factor_memory_deduplicates_forbidden(self, patch_cache_client):
        """Duplicate forbidden directions are merged (only one copy kept)."""
        existing = {
            "version": 1,
            "recommended": [],
            "forbidden": [{"direction": "short-biased"}],
            "insights": [],
            "recent_logs": [],
        }
        patch_cache_client.get.return_value = existing

        memory_patch = {
            "forbidden": [
                {"direction": "short-biased"},  # duplicate
                {"direction": "high-turnover"},  # new
            ],
        }

        result = await update_factor_memory_impl("ws-001", memory_patch)

        directions = [f["direction"] for f in result["memory"]["forbidden"]]
        assert directions.count("short-biased") == 1
        assert "high-turnover" in directions
