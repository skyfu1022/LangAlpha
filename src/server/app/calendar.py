"""Calendar endpoints — economic releases and earnings announcements."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query

from src.data_client.fmp.fmp_client import FMPClient
from src.data_client.tushare import get_tushare_client
from src.server.models.market import validate_market
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
    from_date: Optional[str], to_date: Optional[str], market: str = "us"
) -> tuple[str, str]:
    """Fill in missing dates with today → today+7 (market-aware timezone)."""
    tz = ZoneInfo("Asia/Shanghai") if market == "cn" else ZoneInfo("America/New_York")
    today = datetime.now(tz).date()
    if not from_date:
        from_date = today.isoformat()
    if not to_date:
        to_date = (today + timedelta(days=7)).isoformat()
    return from_date, to_date


async def _fetch_cn_earnings(
    from_date: str, to_date: str
) -> list[EarningsEvent]:
    """通过 Tushare 获取 A 股财报日期。

    TuShare disclosure_date 接口按财报周期查询，不是日期范围。
    策略：查出当前和相邻季度的财报披露计划，再按 ann_date 筛选。
    """
    # 确定需要查询的财报周期（季度末日期）
    from_dt = datetime.strptime(from_date, "%Y-%m-%d")
    periods = set()
    for offset in (-1, 0, 1, 2, 3):
        d = from_dt + timedelta(days=offset * 90)
        # 季度末：3/31, 6/30, 9/30, 12/31
        quarter_end_month = ((d.month - 1) // 3 + 1) * 3
        if quarter_end_month > 12:
            year = d.year + 1
            quarter_end_month = 3
        else:
            year = d.year
        periods.add(f"{year}{quarter_end_month:02d}30" if quarter_end_month in (6, 9) else f"{year}{quarter_end_month:02d}31")

    try:
        client = await get_tushare_client()
        all_raw: list[dict] = []
        for period in periods:
            try:
                batch = await client.get_disclosure_dates(period=period)
                if batch:
                    all_raw.extend(batch)
            except Exception as e:
                logger.warning("tushare.disclosure_date.period=%s error: %s", period, e)
    except Exception as e:
        logger.error("tushare.earnings.error: %s", e)
        return []

    # 按日期范围筛选 ann_date / actual_date
    from_yyyymmdd = from_date.replace("-", "")
    to_yyyymmdd = to_date.replace("-", "")

    events: list[EarningsEvent] = []
    for r in all_raw:
        ts_code = r.get("ts_code", "")
        ann_date = r.get("ann_date") or r.get("actual_date", "")
        if not ts_code or not ann_date:
            continue
        # 筛选：公告日期在范围内
        if ann_date < from_yyyymmdd or ann_date > to_yyyymmdd:
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
    market = validate_market(market)
    from_date, to_date = _default_dates(from_date, to_date, market=market)

    # Check cache
    cached = await _earnings_cache.get(from_date, to_date, market=market)
    if cached is not None:
        events = [EarningsEvent(**item) for item in cached]
        return EarningsCalendarResponse(data=events, count=len(events))

    if market == "cn":
        events = await _fetch_cn_earnings(from_date, to_date)
    else:
        events = await _fetch_us_earnings(from_date, to_date)

    if events:
        await _earnings_cache.set(
            [e.model_dump() for e in events], from_date, to_date, market=market
        )
    return EarningsCalendarResponse(data=events, count=len(events))
