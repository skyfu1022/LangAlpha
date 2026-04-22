"""Calendar endpoints — economic releases and earnings announcements."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.data_client.fmp.fmp_client import FMPClient
from src.data_client.tushare import get_tushare_client
from src.server.models.calendar import (
    EarningsCalendarResponse,
    EarningsEvent,
    EconomicCalendarResponse,
    EconomicEvent,
)
from src.server.services.cache.earnings_cache_service import EarningsCacheService
from src.server.utils.api import CurrentUserId

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/calendar", tags=["Calendar"])

_earnings_cache = EarningsCacheService()


def _default_dates(
    from_date: Optional[str], to_date: Optional[str]
) -> tuple[str, str]:
    """Fill in missing dates with today → today+7."""
    today = date.today()
    if not from_date:
        from_date = today.isoformat()
    if not to_date:
        to_date = (today + timedelta(days=7)).isoformat()
    return from_date, to_date


async def _fetch_cn_earnings(
    from_date: str, to_date: str
) -> list[EarningsEvent]:
    """通过 Tushare 获取 A 股财报日期。"""
    try:
        client = await get_tushare_client()
        raw = await client.get_disclosure_dates(from_date, to_date)
    except Exception as e:
        logger.error("tushare.earnings.error: %s", e)
        return []

    events: list[EarningsEvent] = []
    for r in raw:
        ts_code = r.get("ts_code", "")
        ann_date = r.get("ann_date") or r.get("actual_date", "")
        if not ts_code or not ann_date:
            continue
        if len(ann_date) == 8:
            formatted = f"{ann_date[:4]}-{ann_date[4:6]}-{ann_date[6:8]}"
        else:
            formatted = ann_date
        events.append(EarningsEvent(symbol=ts_code, date=formatted))
    return events


async def _fetch_us_earnings(
    from_date: str, to_date: str
) -> list[EarningsEvent]:
    """通过 FMP 获取美股 earnings。"""
    try:
        fmp_client = FMPClient()
    except (ValueError, ImportError):
        return []

    try:
        raw = await fmp_client.get_earnings_calendar_by_date(
            from_date=from_date, to_date=to_date
        )
        items = raw or []
        return [EarningsEvent(**item) for item in items]
    except Exception as e:
        logger.error("Error fetching US earnings calendar: %s", e)
        return []
    finally:
        await fmp_client.close()


@router.get("/economic", response_model=EconomicCalendarResponse)
async def get_economic_calendar(
    user_id: CurrentUserId,
    from_date: Optional[str] = Query(
        None, alias="from", description="Start date (YYYY-MM-DD). Defaults to today."
    ),
    to_date: Optional[str] = Query(
        None, alias="to", description="End date (YYYY-MM-DD). Defaults to today+7."
    ),
) -> EconomicCalendarResponse:
    """Get upcoming and past economic data releases (GDP, CPI, etc.)."""
    from_date, to_date = _default_dates(from_date, to_date)

    try:
        fmp_client = FMPClient()
    except (ValueError, ImportError):
        # FMP unavailable — no fallback for economic calendar
        return EconomicCalendarResponse(data=[], count=0)

    try:
        try:
            raw = await fmp_client.get_economic_calendar(
                from_date=from_date, to_date=to_date
            )
            events = [EconomicEvent(**item) for item in (raw or [])]
            return EconomicCalendarResponse(data=events, count=len(events))
        finally:
            await fmp_client.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching economic calendar: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/earnings", response_model=EarningsCalendarResponse)
async def get_earnings_calendar(
    user_id: CurrentUserId,
    from_date: Optional[str] = Query(
        None, alias="from", description="Start date (YYYY-MM-DD). Defaults to today."
    ),
    to_date: Optional[str] = Query(
        None, alias="to", description="End date (YYYY-MM-DD). Defaults to today+7."
    ),
    market: Optional[str] = Query(
        None, description="Market filter: 'us' or 'cn'. Defaults to 'us'."
    ),
) -> EarningsCalendarResponse:
    """Get upcoming and past earnings announcements with EPS and revenue data."""
    from_date, to_date = _default_dates(from_date, to_date)

    # Check cache
    cached = await _earnings_cache.get(from_date, to_date, market=market)
    if cached is not None:
        events = [EarningsEvent(**item) for item in cached]
        return EarningsCalendarResponse(data=events, count=len(events))

    if market == "cn":
        events = await _fetch_cn_earnings(from_date, to_date)
    else:
        events = await _fetch_us_earnings(from_date, to_date)

    await _earnings_cache.set(
        [e.model_dump() for e in events], from_date, to_date, market=market
    )
    return EarningsCalendarResponse(data=events, count=len(events))
