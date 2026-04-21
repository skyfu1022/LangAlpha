"""TuShare Pro data source module (A-shares: Shanghai & Shenzhen)."""

from __future__ import annotations

import asyncio
from typing import Optional

from .client import TuShareClient

__all__ = ["TuShareClient", "get_tushare_client", "close_tushare_client"]

_tushare_client: Optional[TuShareClient] = None
_client_lock = asyncio.Lock()


async def get_tushare_client() -> TuShareClient:
    global _tushare_client
    async with _client_lock:
        if _tushare_client is None:
            _tushare_client = TuShareClient()
        return _tushare_client


async def close_tushare_client() -> None:
    global _tushare_client
    async with _client_lock:
        if _tushare_client is not None:
            await _tushare_client.close()
            _tushare_client = None
