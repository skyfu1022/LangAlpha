"""
Tests for cache key market dimension in earnings_cache_service and news_cache_service.

Covers:
- Earnings cache key includes market when provided
- Earnings cache key defaults to 'us' when market is None
- Same params with different market produce different earnings cache keys
- News cache key includes market dimension
- Same params with different market produce different news cache keys
- News cache key defaults to 'us' when market is None
"""

from src.server.services.cache.earnings_cache_service import _cache_key as earnings_cache_key
from src.server.services.cache.news_cache_service import _cache_key as news_cache_key


# ---------------------------------------------------------------------------
# Earnings cache key
# ---------------------------------------------------------------------------


class TestEarningsCacheKey:
    def test_includes_market_us(self):
        key = earnings_cache_key("2026-04-22", "2026-04-30", market="us")
        assert "us" in key
        assert key == "earnings:2026-04-22:2026-04-30:us"

    def test_includes_market_cn(self):
        key = earnings_cache_key("2026-04-22", "2026-04-30", market="cn")
        assert "cn" in key
        assert key == "earnings:2026-04-22:2026-04-30:cn"

    def test_defaults_to_us_when_none(self):
        key = earnings_cache_key("2026-04-22", "2026-04-30", market=None)
        assert key == "earnings:2026-04-22:2026-04-30:us"

    def test_different_markets_produce_different_keys(self):
        key_us = earnings_cache_key("2026-04-22", "2026-04-30", market="us")
        key_cn = earnings_cache_key("2026-04-22", "2026-04-30", market="cn")
        key_none = earnings_cache_key("2026-04-22", "2026-04-30", market=None)
        assert key_us != key_cn
        assert key_us == key_none  # None defaults to us

    def test_different_dates_produce_different_keys(self):
        key1 = earnings_cache_key("2026-04-22", "2026-04-30", market="us")
        key2 = earnings_cache_key("2026-04-23", "2026-04-30", market="us")
        assert key1 != key2


# ---------------------------------------------------------------------------
# News cache key
# ---------------------------------------------------------------------------


class TestNewsCacheKey:
    def test_general_news_includes_market(self):
        key = news_cache_key(tickers=None, limit=20, market="us")
        assert key == "news:us:general:20"

    def test_general_news_market_cn(self):
        key = news_cache_key(tickers=None, limit=20, market="cn")
        assert key == "news:cn:general:20"

    def test_general_news_defaults_to_us_when_none(self):
        key = news_cache_key(tickers=None, limit=20, market=None)
        assert key == "news:us:general:20"

    def test_ticker_news_includes_market(self):
        key = news_cache_key(tickers=["AAPL", "MSFT"], limit=10, market="us")
        assert key == "news:us:tickers:AAPL,MSFT:10"

    def test_ticker_news_sorted_alphabetically(self):
        """Tickers are sorted alphabetically in the key."""
        key = news_cache_key(tickers=["MSFT", "AAPL"], limit=10, market="us")
        assert key == "news:us:tickers:AAPL,MSFT:10"

    def test_ticker_news_market_cn(self):
        key = news_cache_key(tickers=["600519.SH"], limit=10, market="cn")
        assert key == "news:cn:tickers:600519.SH:10"

    def test_different_markets_produce_different_keys(self):
        key_us = news_cache_key(tickers=["AAPL"], limit=20, market="us")
        key_cn = news_cache_key(tickers=["AAPL"], limit=20, market="cn")
        key_none = news_cache_key(tickers=["AAPL"], limit=20, market=None)
        assert key_us != key_cn
        assert key_us == key_none  # None defaults to us
        assert key_cn != key_none

    def test_different_limits_produce_different_keys(self):
        key1 = news_cache_key(tickers=None, limit=20, market="us")
        key2 = news_cache_key(tickers=None, limit=50, market="us")
        assert key1 != key2
