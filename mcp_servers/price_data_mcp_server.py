#!/usr/bin/env python3
"""Price Data MCP Server.

Provides normalized OHLCV time series data and short sale analytics via MCP.

Design goals:
- Small, stable tool surface (high PTC value)
- Normalized JSON output (schema stable across providers)
- Can run in sandbox (stdio) for OSS/dev
- Can be deployed externally (http/sse) for production

Tools:
- get_stock_data: stock OHLCV
- get_asset_data: stock/commodity/crypto/forex OHLCV
- get_short_data: short interest (bi-monthly) and short volume (daily)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Literal, Optional

from mcp.server.fastmcp import FastMCP

from data_client.fmp import get_fmp_client, close_fmp_client
from data_client.ginlix_data import (
    DAILY_INTERVALS,
    close_ginlix_mcp_client,
    get_ginlix_mcp_client,
)
from data_client.market_data_provider import is_us_symbol
from data_client.normalize import normalize_bars


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

_ginlix = get_ginlix_mcp_client()

_INTRADAY_INTERVALS_STOCK = {"1min", "5min", "15min", "30min", "1hour", "4hour"}
_INTRADAY_INTERVALS_ASSET = {"1min", "5min", "1hour"}


@asynccontextmanager
async def _lifespan(app):
    try:
        yield
    finally:
        await close_ginlix_mcp_client()
        await close_fmp_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_MISSING_DATES_ERROR = {
    "error": "start_date and end_date are required for intraday intervals. "
    "Use YYYY-MM-DD or YYYY-MM-DD HH:MM format.",
}


def _ginlix_result_to_response(
    result: list[dict] | dict | None,
    symbol: str,
    interval: str,
    **extra: Any,
) -> dict | None:
    """Convert ``fetch_stock_data`` result to a tool response dict.

    Returns ``dict`` (success or error) or ``None`` (not available → try fallback).
    """
    if result is None:
        return None
    if isinstance(result, dict):
        return result  # error dict
    return {
        **extra,
        "symbol": symbol,
        "interval": interval,
        "count": len(result),
        "rows": result,
        "source": "ginlix-data",
    }


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = FastMCP("PriceDataMCP", lifespan=_lifespan)


@mcp.tool()
async def get_stock_data(
    symbol: str,
    interval: str = "1day",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Get normalized OHLCV for a stock symbol.

    Timestamps are in exchange-local time (e.g., US Eastern for US stocks,
    HKT for .HK, CST for .SS/.SZ).

    Args:
        symbol: Stock ticker (e.g., AAPL, MSFT, 600519.SS, 0700.HK)
        interval: "1day"/"daily" or intraday: 1s/1min/5min/15min/30min/1hour/4hour
        start_date: YYYY-MM-DD (required). Append HH:MM for intraday time filtering.
        end_date: YYYY-MM-DD (required). Append HH:MM for intraday time filtering.

    Returns:
        dict with symbol, interval, count, rows, source.
        rows are normalized: date/open/high/low/close/volume (descending by date).
    """
    interval_lower = interval.lower()

    # 1s interval: ginlix-data only, US stocks only
    if interval_lower == "1s":
        if not is_us_symbol(symbol):
            return {"error": "1-second interval is only available for US stocks."}
        if not start_date or not end_date:
            return {
                "error": "start_date and end_date are required for 1s interval. "
                "Use YYYY-MM-DD or YYYY-MM-DD HH:MM format.",
            }
        if not await _ginlix.ensure():
            return {
                "error": "1-second interval requires ginlix-data (not configured). "
                "Use 1min or higher with FMP.",
            }
        result = await _ginlix.fetch_stock_data(symbol, interval_lower, start_date, end_date)
        resp = _ginlix_result_to_response(result, symbol, interval_lower)
        return resp or {"error": "Failed to fetch 1s data from ginlix-data."}

    # Try ginlix-data first (if available)
    ginlix_result = await _ginlix.fetch_stock_data(symbol, interval_lower, start_date, end_date)
    ginlix_resp = _ginlix_result_to_response(ginlix_result, symbol, interval_lower)
    if ginlix_resp is not None:
        return ginlix_resp

    # Fall back to FMP
    try:
        client = await get_fmp_client()
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to initialize FMP client: {e}"}

    try:
        if interval_lower in DAILY_INTERVALS:
            rows = await client.get_stock_price(symbol, from_date=start_date, to_date=end_date)
        else:
            if interval_lower not in _INTRADAY_INTERVALS_STOCK:
                return {
                    "error": "Unsupported interval for stock",
                    "supported": sorted(DAILY_INTERVALS | _INTRADAY_INTERVALS_STOCK),
                }

            if not start_date or not end_date:
                return _MISSING_DATES_ERROR
            rows = await client.get_intraday_chart(
                symbol,
                interval_lower,
                from_date=start_date,
                to_date=end_date,
            )
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}

    normalized = normalize_bars(rows or [], symbol)
    return {
        "symbol": symbol,
        "interval": interval_lower,
        "count": len(normalized),
        "rows": normalized,
        "source": "fmp",
    }


@mcp.tool()
async def get_asset_data(
    symbol: str,
    asset_type: str,
    interval: str = "daily",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> dict:
    """Get normalized OHLCV for stock/commodity/crypto/forex.

    Timestamps are in exchange-local time (e.g., US Eastern for US stocks,
    HKT for .HK, CST for .SS/.SZ).

    Args:
        symbol: Asset symbol (e.g., GCUSD, BTCUSD, EURUSD, AAPL)
        asset_type: one of stock/commodity/crypto/forex
        interval: daily/1day or intraday
          - stock: 1s/1min/5min/15min/30min/1hour/4hour
          - commodity/crypto/forex: 1min/5min/1hour
        from_date: YYYY-MM-DD (required). Append HH:MM for intraday time filtering.
        to_date: YYYY-MM-DD (required). Append HH:MM for intraday time filtering.

    Returns:
        dict with symbol, asset_type, interval, count, rows (descending), source.
    """
    at = asset_type.lower().strip()
    interval_lower = interval.lower()

    if at not in {"stock", "commodity", "crypto", "forex"}:
        return {"error": "Invalid asset_type", "supported": ["stock", "commodity", "crypto", "forex"]}

    # Stock: ginlix-data → FMP fallback
    if at == "stock":
        # 1s interval: ginlix-data only, US stocks only
        if interval_lower == "1s":
            if not is_us_symbol(symbol):
                return {"error": "1-second interval is only available for US stocks."}
            if not from_date or not to_date:
                return {
                    "error": "from_date and to_date are required for 1s interval. "
                    "Use YYYY-MM-DD or YYYY-MM-DD HH:MM format.",
                }
            if not await _ginlix.ensure():
                return {
                    "error": "1-second interval requires ginlix-data (not configured). "
                    "Use 1min or higher with FMP.",
                }
            result = await _ginlix.fetch_stock_data(symbol, interval_lower, from_date, to_date)
            resp = _ginlix_result_to_response(result, symbol, interval_lower, asset_type=at)
            return resp or {"error": "Failed to fetch 1s data from ginlix-data."}

        # Try ginlix-data first
        ginlix_result = await _ginlix.fetch_stock_data(symbol, interval_lower, from_date, to_date)
        ginlix_resp = _ginlix_result_to_response(ginlix_result, symbol, interval_lower, asset_type=at)
        if ginlix_resp is not None:
            return ginlix_resp

    # FMP path (all asset types, stock fallback)
    try:
        client = await get_fmp_client()
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to initialize FMP client: {e}"}

    try:
        if at == "stock":
            if interval_lower in DAILY_INTERVALS:
                rows = await client.get_stock_price(symbol, from_date=from_date, to_date=to_date)
            else:
                if interval_lower not in _INTRADAY_INTERVALS_STOCK:
                    return {
                        "error": "Unsupported interval for stock",
                        "supported": sorted(DAILY_INTERVALS | _INTRADAY_INTERVALS_STOCK),
                    }
                if not from_date or not to_date:
                    return _MISSING_DATES_ERROR
                rows = await client.get_intraday_chart(
                    symbol,
                    interval_lower,
                    from_date=from_date,
                    to_date=to_date,
                )
        else:
            if interval_lower in DAILY_INTERVALS:
                if at == "commodity":
                    rows = await client.get_commodity_price(symbol, from_date=from_date, to_date=to_date)
                elif at == "crypto":
                    rows = await client.get_crypto_price(symbol, from_date=from_date, to_date=to_date)
                else:
                    rows = await client.get_forex_price(symbol, from_date=from_date, to_date=to_date)
            else:
                if interval_lower not in _INTRADAY_INTERVALS_ASSET:
                    return {
                        "error": "Unsupported interval for commodity/crypto/forex",
                        "supported": sorted(DAILY_INTERVALS | _INTRADAY_INTERVALS_ASSET),
                    }
                if not from_date or not to_date:
                    return _MISSING_DATES_ERROR
                if at == "commodity":
                    rows = await client.get_commodity_intraday_chart(
                        symbol, interval_lower, from_date=from_date, to_date=to_date,
                    )
                elif at == "crypto":
                    rows = await client.get_crypto_intraday_chart(
                        symbol, interval_lower, from_date=from_date, to_date=to_date,
                    )
                else:
                    rows = await client.get_forex_intraday_chart(
                        symbol, interval_lower, from_date=from_date, to_date=to_date,
                    )
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}

    normalized = normalize_bars(rows or [], symbol)
    return {
        "symbol": symbol,
        "asset_type": at,
        "interval": interval_lower,
        "count": len(normalized),
        "rows": normalized,
        "source": "fmp",
    }


@mcp.tool()
async def get_short_data(
    symbol: str,
    data_type: Literal["short_interest", "short_volume", "both"] = "both",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Get short interest and/or short volume data for a stock.

    Short interest is reported bi-monthly by FINRA (settlement_date).
    Short volume is reported daily from off-exchange venues (date).

    Args:
        symbol: Stock ticker (e.g., AAPL, GME, AMC)
        data_type: "short_interest", "short_volume", or "both" (default)
        from_date: YYYY-MM-DD start date filter (optional)
        to_date: YYYY-MM-DD end date filter (optional)
        limit: Max records per type (default 20, max 50000)

    Returns:
        dict with short_interest and/or short_volume arrays (newest first).
        short_interest fields: ticker, settlement_date, short_interest, avg_daily_volume, days_to_cover
        short_volume fields: ticker, date, short_volume, total_volume, short_volume_ratio, exempt_volume, non_exempt_volume
    """
    return await _ginlix.fetch_short_data(
        symbol, data_type=data_type, from_date=from_date, to_date=to_date, limit=limit,
    )


if __name__ == "__main__":
    mcp.run()
