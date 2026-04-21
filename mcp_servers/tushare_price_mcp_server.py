"""TuShare Price MCP Server.

Provides A-share (Shanghai & Shenzhen) stock price data via TuShare Pro API.

Tools:
- get_a_share_daily: Daily OHLCV data for A-share stocks
- get_a_share_intraday: Intraday OHLCV data for A-share stocks
- get_a_share_basic: Basic stock information for A-share equities
"""

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOKEN = os.getenv("TUSHARE_API_KEY", "")
_BASE_URL = "https://api.tushare.pro"


async def _tushare_request(
    api_name: str,
    params: dict[str, Any] | None = None,
    fields: str | None = None,
) -> list[dict[str, Any]]:
    """Send a request to TuShare API and return rows as dicts."""
    import httpx

    body: dict[str, Any] = {"api_name": api_name, "token": _TOKEN}
    if params:
        body["params"] = params
    if fields:
        body["fields"] = fields

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(_BASE_URL, json=body)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"TuShare API error ({api_name}): {data.get('msg')}")

    payload = data.get("data", {})
    field_names = payload.get("fields", [])
    items = payload.get("items", [])
    return [dict(zip(field_names, row)) for row in items]


def _to_ts_code(symbol: str) -> str:
    """Convert symbol to TuShare ts_code format."""
    if "." in symbol:
        return symbol
    if symbol.startswith(("6", "9")):
        return f"{symbol}.SH"
    return f"{symbol}.SZ"


def _make_response(
    data_type: str, data: Any, count: int | None = None, **extra: Any
) -> dict:
    resp = {"data_type": data_type, "source": "tushare", "data": data}
    if count is not None:
        resp["count"] = count
    elif isinstance(data, list):
        resp["count"] = len(data)
    resp.update(extra)
    return resp


def _make_error(msg: str) -> dict:
    return {"error": msg}


def _normalize_daily(row: dict[str, Any]) -> dict[str, Any]:
    trade_date = row.get("trade_date", "")
    return {
        "date": f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}",
        "open": float(row.get("open", 0)),
        "high": float(row.get("high", 0)),
        "low": float(row.get("low", 0)),
        "close": float(row.get("close", 0)),
        "volume": int(row.get("vol", 0) or 0),
        "change": float(row.get("change", 0)),
        "pct_chg": float(row.get("pct_chg", 0)),
    }


def _normalize_intraday(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": row.get("trade_time", ""),
        "open": float(row.get("open", 0)),
        "high": float(row.get("high", 0)),
        "low": float(row.get("low", 0)),
        "close": float(row.get("close", 0)),
        "volume": int(row.get("vol", 0) or 0),
    }


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = FastMCP("TuSharePriceMCP")


@mcp.tool()
async def get_a_share_daily(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Get daily OHLCV data for A-share stocks (Shanghai & Shenzhen).

    Returns bars with date, open, high, low, close, volume, change, pct_chg.
    Supports stocks like 000001.SZ (Ping An Bank), 600000.SH (Pudong Development Bank).

    Args:
        symbol: Stock code in TuShare format (e.g. 000001.SZ, 600000.SH) or plain code (e.g. 000001)
        start_date: Start date in YYYYMMDD format (optional)
        end_date: End date in YYYYMMDD format (optional)
    """
    try:
        ts_code = _to_ts_code(symbol)
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date.replace("-", "")
        if end_date:
            params["end_date"] = end_date.replace("-", "")

        data = await _tushare_request("daily", params)
        if not data:
            return _make_error(f"No daily data found for {symbol}")
        bars = [_normalize_daily(r) for r in data]
        return _make_response("a_share_daily", bars, symbol=ts_code)
    except Exception as e:  # noqa: BLE001
        return _make_error(f"Failed to fetch daily data for {symbol}: {e}")


@mcp.tool()
async def get_a_share_intraday(
    symbol: str,
    freq: str = "5min",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Get intraday OHLCV data for A-share stocks (requires TuShare 5000+ points).

    Returns bars with date (YYYY-MM-DD HH:MM:SS), open, high, low, close, volume.

    Args:
        symbol: Stock code in TuShare format (e.g. 000001.SZ) or plain code (e.g. 000001)
        freq: Bar frequency — 1min, 5min, 15min, 30min, 60min
        start_date: Start date-time (YYYYMMDD HH:MM:SS format, optional)
        end_date: End date-time (YYYYMMDD HH:MM:SS format, optional)
    """
    try:
        ts_code = _to_ts_code(symbol)
        params: dict[str, Any] = {"ts_code": ts_code, "freq": freq}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        data = await _tushare_request("stk_mins", params)
        if not data:
            return _make_error(f"No intraday data found for {symbol}")
        bars = [_normalize_intraday(r) for r in data]
        return _make_response("a_share_intraday", bars, symbol=ts_code, freq=freq)
    except Exception as e:  # noqa: BLE001
        return _make_error(f"Failed to fetch intraday data for {symbol}: {e}")


@mcp.tool()
async def get_a_share_basic(
    symbol: str | None = None,
) -> dict:
    """Get basic stock information for A-share equities.

    Returns list of stocks with ts_code, name, area, industry, market, list_date.

    Args:
        symbol: Optional stock code to filter (e.g. 000001.SZ or 000001)
    """
    try:
        params: dict[str, Any] = {"list_status": "L"}
        if symbol:
            params["ts_code"] = _to_ts_code(symbol)

        data = await _tushare_request("stock_basic", params)
        if not data:
            return _make_error(f"No stock info found for {symbol or 'all'}")
        return _make_response("a_share_basic", data, symbol=symbol or "all")
    except Exception as e:  # noqa: BLE001
        return _make_error(f"Failed to fetch stock info: {e}")


if __name__ == "__main__":
    mcp.run(transport="stdio")
