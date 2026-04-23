"""
Tests for _filter_by_market in src/server/app/news.py.

Covers:
- market=None returns all articles unchanged
- market="us" keeps US-only tickers, excludes CN-only tickers
- market="cn" keeps CN tickers (.SH/.SZ/.SS), excludes US-only tickers
- Articles with no tickers pass through for both markets (general news)
- Mixed tickers included only in CN market (has CN suffix)
- Unknown market value: only no-ticker articles pass through
"""

import pytest

from src.server.app.news import _filter_by_market


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_US_ARTICLE = {
    "id": "us-1",
    "title": "Apple earnings beat",
    "tickers": ["AAPL", "MSFT"],
}

_CN_ARTICLE_SH = {
    "id": "cn-1",
    "title": "Kweichow Moutai report",
    "tickers": ["600519.SH"],
}

_CN_ARTICLE_SZ = {
    "id": "cn-2",
    "title": "Ping An results",
    "tickers": ["000001.SZ"],
}

_CN_ARTICLE_SS = {
    "id": "cn-3",
    "title": "Shanghai article",
    "tickers": ["600000.SS"],
}

_MIXED_ARTICLE = {
    "id": "mixed-1",
    "title": "Global markets mixed",
    "tickers": ["AAPL", "600519.SH"],
}

_NO_TICKERS_ARTICLE = {
    "id": "no-tickers-1",
    "title": "General market news",
    "tickers": [],
}

_MISSING_TICKERS_ARTICLE = {
    "id": "missing-tickers-1",
    "title": "No tickers key",
}


# ---------------------------------------------------------------------------
# market=None
# ---------------------------------------------------------------------------


def test_market_none_returns_all_articles():
    articles = [_US_ARTICLE, _CN_ARTICLE_SH, _MIXED_ARTICLE]
    result = _filter_by_market(articles, None)
    assert result == articles


def test_market_empty_string_returns_all_articles():
    articles = [_US_ARTICLE, _CN_ARTICLE_SH]
    result = _filter_by_market(articles, "")
    assert result == articles


# ---------------------------------------------------------------------------
# market="us"
# ---------------------------------------------------------------------------


def test_market_us_includes_us_tickers():
    articles = [_US_ARTICLE]
    result = _filter_by_market(articles, "us")
    assert len(result) == 1
    assert result[0]["id"] == "us-1"


def test_market_us_excludes_cn_tickers():
    articles = [_CN_ARTICLE_SH, _CN_ARTICLE_SZ, _CN_ARTICLE_SS]
    result = _filter_by_market(articles, "us")
    assert result == []


def test_market_us_includes_no_tickers():
    """Articles with empty tickers are general news — pass through for US."""
    articles = [_NO_TICKERS_ARTICLE]
    result = _filter_by_market(articles, "us")
    assert len(result) == 1
    assert result[0]["id"] == "no-tickers-1"


def test_market_us_includes_missing_tickers_key():
    """Articles with no 'tickers' key are general news — pass through for US."""
    articles = [_MISSING_TICKERS_ARTICLE]
    result = _filter_by_market(articles, "us")
    assert len(result) == 1
    assert result[0]["id"] == "missing-tickers-1"


def test_market_us_filters_mixed_list():
    """From a mixed list, US articles and no-ticker articles survive."""
    articles = [
        _US_ARTICLE,
        _CN_ARTICLE_SH,
        _NO_TICKERS_ARTICLE,
        _MIXED_ARTICLE,
    ]
    result = _filter_by_market(articles, "us")
    ids = {a["id"] for a in result}
    # US article and no-tickers pass; CN excluded; mixed has CN suffix so excluded
    assert _US_ARTICLE["id"] in ids
    assert _NO_TICKERS_ARTICLE["id"] in ids
    assert _CN_ARTICLE_SH["id"] not in ids
    assert _MIXED_ARTICLE["id"] not in ids


# ---------------------------------------------------------------------------
# market="cn"
# ---------------------------------------------------------------------------


def test_market_cn_includes_sh_suffix():
    articles = [_CN_ARTICLE_SH]
    result = _filter_by_market(articles, "cn")
    assert len(result) == 1
    assert result[0]["id"] == "cn-1"


def test_market_cn_includes_sz_suffix():
    articles = [_CN_ARTICLE_SZ]
    result = _filter_by_market(articles, "cn")
    assert len(result) == 1
    assert result[0]["id"] == "cn-2"


def test_market_cn_includes_ss_suffix():
    articles = [_CN_ARTICLE_SS]
    result = _filter_by_market(articles, "cn")
    assert len(result) == 1
    assert result[0]["id"] == "cn-3"


def test_market_cn_excludes_us_tickers():
    articles = [_US_ARTICLE]
    result = _filter_by_market(articles, "cn")
    assert result == []


def test_market_cn_includes_no_tickers():
    """Articles with empty tickers are general news — pass through for CN too."""
    articles = [_NO_TICKERS_ARTICLE]
    result = _filter_by_market(articles, "cn")
    assert len(result) == 1
    assert result[0]["id"] == "no-tickers-1"


def test_market_cn_includes_missing_tickers_key():
    """Articles with no tickers key are general news — pass through for CN."""
    articles = [_MISSING_TICKERS_ARTICLE]
    result = _filter_by_market(articles, "cn")
    assert len(result) == 1
    assert result[0]["id"] == "missing-tickers-1"


def test_market_cn_filters_mixed_list():
    """From a mixed list, CN articles, mixed articles, and no-ticker articles survive."""
    articles = [
        _US_ARTICLE,
        _CN_ARTICLE_SH,
        _NO_TICKERS_ARTICLE,
        _MIXED_ARTICLE,
    ]
    result = _filter_by_market(articles, "cn")
    ids = {a["id"] for a in result}
    assert _CN_ARTICLE_SH["id"] in ids
    assert _MIXED_ARTICLE["id"] in ids
    assert _NO_TICKERS_ARTICLE["id"] in ids
    assert _US_ARTICLE["id"] not in ids


# ---------------------------------------------------------------------------
# Mixed tickers
# ---------------------------------------------------------------------------


def test_mixed_tickers_included_in_cn_excluded_from_us():
    """Article with both US and CN tickers: included in CN (has CN suffix),
    excluded from US (has CN suffix)."""
    articles = [_MIXED_ARTICLE]

    us_result = _filter_by_market(articles, "us")
    assert len(us_result) == 0

    cn_result = _filter_by_market(articles, "cn")
    assert len(cn_result) == 1
    assert cn_result[0]["id"] == "mixed-1"


# ---------------------------------------------------------------------------
# Unknown market
# ---------------------------------------------------------------------------


def test_unknown_market_only_passes_no_ticker_articles():
    """Unknown market value: only general (no-ticker) articles pass through,
    as neither cn nor us condition matches."""
    articles = [
        _US_ARTICLE,
        _CN_ARTICLE_SH,
        _MIXED_ARTICLE,
        _NO_TICKERS_ARTICLE,
    ]
    result = _filter_by_market(articles, "eu")
    assert len(result) == 1
    assert result[0]["id"] == "no-tickers-1"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_articles_list():
    assert _filter_by_market([], "us") == []
    assert _filter_by_market([], "cn") == []
    assert _filter_by_market([], None) == []


def test_tickers_as_none():
    """Article with tickers=None treated as empty list -> general news."""
    article = {"id": "none-tickers", "title": "t", "tickers": None}
    us_result = _filter_by_market([article], "us")
    assert len(us_result) == 1

    cn_result = _filter_by_market([article], "cn")
    assert len(cn_result) == 1  # general news passes through for CN too


def test_ticker_suffix_case_insensitive():
    """CN suffix detection is case-insensitive."""
    article = {"id": "lower-cn", "title": "t", "tickers": ["600519.sh"]}
    cn_result = _filter_by_market([article], "cn")
    assert len(cn_result) == 1

    us_result = _filter_by_market([article], "us")
    assert len(us_result) == 0
