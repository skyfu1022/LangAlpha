from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import create_test_app


@pytest_asyncio.fixture
async def client():
    from src.server.app.market_data import router

    app = create_test_app(router)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


class TestStockFundamentalsProtection:
    @pytest.mark.asyncio
    async def test_company_overview_rejects_index_symbol(self, client):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        with (
            patch("src.utils.cache.redis_cache.get_cache_client", return_value=cache),
            patch(
                "src.tools.market_data.implementations.fetch_company_overview_data",
                new=AsyncMock(),
            ) as fetch_overview,
        ):
            resp = await client.get("/api/v1/market-data/stocks/%5E000001.SH/overview")

        assert resp.status_code == 422
        assert "Index symbols are not supported" in resp.json()["detail"]
        fetch_overview.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_analyst_data_rejects_index_symbol(self, client):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        with (
            patch("src.utils.cache.redis_cache.get_cache_client", return_value=cache),
            patch(
                "src.data_client.get_financial_data_provider",
                new=AsyncMock(),
            ) as get_provider,
        ):
            resp = await client.get("/api/v1/market-data/stocks/%5E000001.SH/analyst-data")

        assert resp.status_code == 422
        assert "Index symbols are not supported" in resp.json()["detail"]
        get_provider.assert_not_awaited()
