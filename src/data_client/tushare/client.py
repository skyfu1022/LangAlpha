"""TuShare API async HTTP client.

TuShare uses a POST-based JSON API at ``https://api.tushare.pro``.
Every request sends ``api_name``, ``token``, ``params`` and ``fields``
in the JSON body.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.tushare.pro"


class TuShareClient:
    """Async HTTP client for the TuShare Pro API."""

    def __init__(self, token: str | None = None, timeout: float = 30.0):
        self._token = token or os.getenv("TUSHARE_API_KEY", "")
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=_BASE_URL,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def _request(
        self,
        api_name: str,
        params: dict[str, Any] | None = None,
        fields: str | None = None,
    ) -> dict[str, Any]:
        """Send a request to the TuShare API and return parsed JSON."""
        body: dict[str, Any] = {
            "api_name": api_name,
            "token": self._token,
        }
        if params:
            body["params"] = params
        if fields:
            body["fields"] = fields

        client = await self._get_client()
        response = await client.post("", json=body)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            msg = data.get("msg", "unknown error")
            raise RuntimeError(f"TuShare API error ({api_name}): {msg}")

        return data

    async def query_dataframe(
        self,
        api_name: str,
        params: dict[str, Any] | None = None,
        fields: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query TuShare and return rows as list of dicts.

        TuShare returns ``{"data": {"fields": [...], "items": [[...], ...]}}``.
        This method zips them into dicts.
        """
        raw = await self._request(api_name, params, fields)
        payload = raw.get("data", {})
        field_names = payload.get("fields", [])
        items = payload.get("items", [])
        return [dict(zip(field_names, row)) for row in items]

    async def get_disclosure_dates(
        self,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """查询财报披露日期。

        Args:
            start_date: 开始日期，格式 YYYYMMDD 或 YYYY-MM-DD
            end_date: 结束日期，格式 YYYYMMDD 或 YYYY-MM-DD
        """
        s = start_date.replace("-", "")
        e = end_date.replace("-", "")
        return await self.query_dataframe(
            api_name="disclosure_date",
            params={"start_date": s, "end_date": e},
            fields="ts_code,ann_date,end_date,report_type,actual_date",
        )

    # ------------------------------------------------------------------
    # Convenience wrappers for common endpoints
    # ------------------------------------------------------------------

    async def daily(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_dataframe("daily", params)

    async def index_daily(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_dataframe("index_daily", params)

    async def index_mins(
        self,
        ts_code: str,
        freq: str = "5min",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"ts_code": ts_code, "freq": freq}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_dataframe("index_mins", params)

    async def stk_mins(
        self,
        ts_code: str,
        freq: str = "5min",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"ts_code": ts_code, "freq": freq}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_dataframe("stk_mins", params)

    async def daily_basic(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self.query_dataframe("daily_basic", params)

    async def stock_basic(
        self,
        ts_code: str | None = None,
        list_status: str = "L",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"list_status": list_status}
        if ts_code:
            params["ts_code"] = ts_code
        return await self.query_dataframe("stock_basic", params)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
