"""TuShare implementation of MarketDataSource.

Provides A-share (Shanghai & Shenzhen) OHLCV data via the TuShare Pro API.
Symbol format: ``000001.SZ`` (Shenzhen), ``600000.SH`` (Shanghai).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .client import TuShareClient

logger = logging.getLogger(__name__)

_CN = ZoneInfo("Asia/Shanghai")

# TuShare minute frequencies mapped from our interval names
_INTERVAL_MAP = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "1hour": "60min",
}


class TuShareDataSource:
    """Market data source backed by TuShare Pro API (A-shares only)."""

    _SUPPORTED_INTERVALS = frozenset(_INTERVAL_MAP.keys())

    # A-share ETF code prefixes: 51xxxx.SH (SSE), 15xxxx.SZ (SZSE), 56xxxx.SH (SSE)
    _ETF_PREFIXES = ("51", "15", "56")

    def __init__(self, client: TuShareClient | None = None):
        self._client = client or TuShareClient()

    @classmethod
    def _is_etf(cls, ts_code: str) -> bool:
        """Heuristic: A-share ETFs start with 51/15/56 and have exchange suffix."""
        base = ts_code.split(".", 1)[0] if "." in ts_code else ts_code
        return base[:2] in cls._ETF_PREFIXES

    @staticmethod
    def _normalize_daily(row: dict[str, Any]) -> dict[str, Any]:
        """Normalize a TuShare daily bar to standard OHLCV shape."""
        trade_date = row.get("trade_date", "")
        try:
            dt = datetime.strptime(trade_date, "%Y%m%d").replace(tzinfo=_CN)
            t = int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            t = 0
        return {
            "time": t,
            "open": float(row.get("open", 0.0)),
            "high": float(row.get("high", 0.0)),
            "low": float(row.get("low", 0.0)),
            "close": float(row.get("close", 0.0)),
            "volume": int(row.get("vol", 0) or 0),
        }

    @staticmethod
    def _normalize_intraday(row: dict[str, Any]) -> dict[str, Any]:
        """Normalize a TuShare intraday bar to standard OHLCV shape."""
        trade_time = row.get("trade_time", "")
        try:
            dt = datetime.strptime(trade_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_CN)
            t = int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            t = 0
        return {
            "time": t,
            "open": float(row.get("open", 0.0)),
            "high": float(row.get("high", 0.0)),
            "low": float(row.get("low", 0.0)),
            "close": float(row.get("close", 0.0)),
            "volume": int(row.get("vol", 0) or 0),
        }

    @staticmethod
    def _to_ts_code(symbol: str) -> str:
        """Convert a symbol to TuShare ts_code format.

        Accepts both ``000001.SZ`` and ``000001`` formats.
        """
        if "." in symbol:
            base, suffix = symbol.rsplit(".", 1)
            suffix = suffix.upper()
            if suffix == "SS":
                suffix = "SH"
            return f"{base}.{suffix}"
        # Infer exchange from leading digit
        if symbol.startswith(("6", "9")):
            return f"{symbol}.SH"
        return f"{symbol}.SZ"

    async def get_intraday(
        self,
        symbol: str,
        interval: str,
        from_date: str | None = None,
        to_date: str | None = None,
        is_index: bool = False,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if interval not in self._SUPPORTED_INTERVALS:
            raise ValueError(
                f"Interval '{interval}' is not supported by TuShare"
            )
        ts_code = self._to_ts_code(symbol)
        # TuShare expects dates as YYYYMMDD
        start = from_date.replace("-", "") if from_date else None
        end = to_date.replace("-", "") if to_date else None

        # ETFs are not true indices — use stock endpoints even when is_index=True
        if is_index and not self._is_etf(ts_code):
            data = await self._client.index_mins(
                ts_code=ts_code,
                freq=_INTERVAL_MAP[interval],
                start_date=start,
                end_date=end,
            )
        else:
            data = await self._client.stk_mins(
                ts_code=ts_code,
                freq=_INTERVAL_MAP[interval],
                start_date=start,
                end_date=end,
            )
        return [self._normalize_intraday(bar) for bar in (data or [])]

    async def get_daily(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        is_index: bool = False,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        ts_code = self._to_ts_code(symbol)
        start = from_date.replace("-", "") if from_date else None
        end = to_date.replace("-", "") if to_date else None

        if is_index and not self._is_etf(ts_code):
            data = await self._client.index_daily(
                ts_code=ts_code,
                start_date=start,
                end_date=end,
            )
        elif self._is_etf(ts_code):
            data = await self._client.fund_daily(
                ts_code=ts_code,
                start_date=start,
                end_date=end,
            )
        else:
            data = await self._client.daily(
                ts_code=ts_code,
                start_date=start,
                end_date=end,
            )
        return [self._normalize_daily(bar) for bar in (data or [])]

    async def get_snapshots(
        self,
        symbols: list[str],
        asset_type: str = "stocks",
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch latest daily data as snapshots (TuShare has no real-time endpoint in basic API)."""
        import asyncio

        results = await asyncio.gather(
            *[self._snapshot_one(s, asset_type=asset_type) for s in symbols],
            return_exceptions=True,
        )
        snapshots: list[dict[str, Any]] = []
        for sym, r in zip(symbols, results):
            if isinstance(r, Exception):
                logger.warning("tushare.snapshot.failed | symbol=%s", sym, exc_info=r)
                continue
            snapshots.append(r)
        return snapshots

    async def _snapshot_one(self, symbol: str, asset_type: str = "stocks") -> dict[str, Any]:
        ts_code = self._to_ts_code(symbol)
        is_etf = self._is_etf(ts_code)

        if asset_type == "indices" and not is_etf:
            data = await self._client.index_daily(ts_code=ts_code)
        elif is_etf:
            data = await self._client.fund_daily(ts_code=ts_code)
        else:
            data = await self._client.daily(ts_code=ts_code)
        if not data:
            return {"symbol": symbol, "price": None}
        row = data[0]
        return {
            "symbol": symbol,
            "name": None,
            "price": float(row.get("close", 0)),
            "change": float(row.get("change", 0)),
            "change_percent": float(row.get("pct_chg", 0)),
            "previous_close": float(row.get("pre_close", 0)),
            "open": float(row.get("open", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "volume": int(row.get("vol", 0) or 0),
            "market_status": None,
        }

    async def get_market_status(
        self,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        from src.utils.market_hours import current_market_phase

        phase = current_market_phase()
        return {
            "market": "open" if phase == "open" else ("extended-hours" if phase in ("pre", "post") else "closed"),
            "afterHours": phase == "post",
            "earlyHours": phase == "pre",
            "serverTime": datetime.now(_CN).isoformat(),
            "exchanges": None,
        }

    async def close(self) -> None:
        await self._client.close()
