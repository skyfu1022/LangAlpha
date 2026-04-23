"""
Tests for _fetch_cn_earnings in src/server/app/calendar.py.

Covers:
- Successful fetch returns list of EarningsEvent with formatted dates
- TuShare client error returns empty list (not exception)
- Empty response from TuShare returns empty list
- Records with missing ts_code or ann_date are skipped
- Date formatting: 8-digit string "20260422" becomes "2026-04-22"
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.server.app.calendar import _fetch_cn_earnings

_TUSHARE_PATH = "src.server.app.calendar.get_tushare_client"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client(raw_data):
    """Build a mock TuShare client whose get_disclosure_dates returns raw_data."""
    client = AsyncMock()
    client.get_disclosure_dates = AsyncMock(return_value=raw_data)
    return client


# ---------------------------------------------------------------------------
# Successful fetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_fetch_returns_earnings_events():
    raw = [
        {"ts_code": "600519.SH", "ann_date": "20260422"},
        {"ts_code": "000001.SZ", "ann_date": "20260423"},
    ]
    mock_client = _make_mock_client(raw)

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-22", "2026-04-30")

    assert len(events) == 2
    assert events[0].symbol == "600519.SH"
    assert events[0].date == "2026-04-22"
    assert events[1].symbol == "000001.SZ"
    assert events[1].date == "2026-04-23"


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_date_formatting_8_digit_string():
    """8-digit ann_date '20260422' becomes '2026-04-22'."""
    raw = [{"ts_code": "600519.SH", "ann_date": "20260422"}]
    mock_client = _make_mock_client(raw)

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-22", "2026-04-22")

    assert len(events) == 1
    assert events[0].date == "2026-04-22"


@pytest.mark.asyncio
async def test_date_formatting_already_formatted():
    """Non-8-digit date string passes through unchanged."""
    raw = [{"ts_code": "600519.SH", "ann_date": "2026-04-22"}]
    mock_client = _make_mock_client(raw)

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-22", "2026-04-22")

    assert len(events) == 1
    assert events[0].date == "2026-04-22"


@pytest.mark.asyncio
async def test_date_formatting_uses_actual_date_fallback():
    """When ann_date is missing, actual_date is used as fallback."""
    raw = [{"ts_code": "600519.SH", "ann_date": None, "actual_date": "20260425"}]
    mock_client = _make_mock_client(raw)

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-25", "2026-04-25")

    assert len(events) == 1
    assert events[0].date == "2026-04-25"


# ---------------------------------------------------------------------------
# TuShare client error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tushare_error_returns_empty_list():
    """Client raising an exception returns [] (not propagation)."""
    mock_client = AsyncMock()
    mock_client.get_disclosure_dates = AsyncMock(
        side_effect=RuntimeError("tushare API timeout")
    )

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-22", "2026-04-30")

    assert events == []


# ---------------------------------------------------------------------------
# Empty response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_response_returns_empty_list():
    mock_client = _make_mock_client([])

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-22", "2026-04-30")

    assert events == []


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_ts_code_skipped():
    """Records without ts_code are silently skipped."""
    raw = [
        {"ann_date": "20260422"},  # missing ts_code
        {"ts_code": "600519.SH", "ann_date": "20260423"},
    ]
    mock_client = _make_mock_client(raw)

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-22", "2026-04-30")

    assert len(events) == 1
    assert events[0].symbol == "600519.SH"


@pytest.mark.asyncio
async def test_missing_ann_date_and_actual_date_skipped():
    """Records without ann_date AND actual_date are skipped."""
    raw = [
        {"ts_code": "600519.SH"},  # missing both dates
        {"ts_code": "000001.SZ", "ann_date": "20260423"},
    ]
    mock_client = _make_mock_client(raw)

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-22", "2026-04-30")

    assert len(events) == 1
    assert events[0].symbol == "000001.SZ"


@pytest.mark.asyncio
async def test_empty_ts_code_skipped():
    """Empty string ts_code is treated as missing and skipped."""
    raw = [
        {"ts_code": "", "ann_date": "20260422"},
        {"ts_code": "600519.SH", "ann_date": "20260423"},
    ]
    mock_client = _make_mock_client(raw)

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-22", "2026-04-30")

    assert len(events) == 1
    assert events[0].symbol == "600519.SH"


@pytest.mark.asyncio
async def test_empty_ann_date_with_actual_date_used():
    """Empty ann_date falls back to actual_date."""
    raw = [
        {"ts_code": "600519.SH", "ann_date": "", "actual_date": "20260425"},
    ]
    mock_client = _make_mock_client(raw)

    with patch(_TUSHARE_PATH, new_callable=AsyncMock, return_value=mock_client):
        events = await _fetch_cn_earnings("2026-04-25", "2026-04-25")

    assert len(events) == 1
    assert events[0].date == "2026-04-25"
