"""News feed endpoint — replaces the infoflow proxy for news sections."""

from __future__ import annotations

import logging

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.server.models.market import validate_market
from src.server.models.news import (
    NewsArticle,
    NewsArticleCompact,
    NewsCompactResponse,
    NewsPublisher,
)
from src.server.services.cache.news_cache_service import NewsCacheService
from src.server.utils.api import CurrentUserId

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/news", tags=["News"])

_cache = NewsCacheService()

_CN_SUFFIXES = ('.SH', '.SZ', '.SS')


def _filter_by_market(articles: list[dict], market: str | None) -> list[dict]:
    """Filter articles by market based on ticker suffixes.

    CN market: keep articles with tickers ending in .SH/.SZ/.SS.
    US market: keep articles WITHOUT such suffixes.
    Articles without tickers are general/macro news — included for all markets.
    No market (None): return all articles unchanged.
    """
    if not market:
        return articles
    filtered = []
    for article in articles:
        tickers = article.get('tickers', []) or []
        if not tickers:
            # Articles without tickers are general/macro news — include for all markets
            filtered.append(article)
            continue
        has_cn = any(str(t).upper().endswith(_CN_SUFFIXES) for t in tickers)
        if market == 'cn' and has_cn:
            filtered.append(article)
        elif market == 'us' and not has_cn:
            filtered.append(article)
        # else: ticker set exists but belongs to the other market — exclude
    return filtered


def _compact(article: dict) -> NewsArticleCompact | None:
    """Convert a full article dict to a compact model. Returns None for invalid articles."""
    title = article.get("title")
    if not title:
        return None
    sentiments = article.get("sentiments")
    article_id = article.get("id")
    source = article.get("source")
    if not article_id or not source:
        return None
    return NewsArticleCompact(
        id=article_id,
        title=title,
        published_at=article.get("published_at", ""),
        image_url=article.get("image_url"),
        article_url=article.get("article_url"),
        source=NewsPublisher(**source),
        tickers=article.get("tickers", []),
        has_sentiment=bool(sentiments and len(sentiments) > 0),
    )


@router.get("", response_model=NewsCompactResponse)
async def get_news(
    user_id: CurrentUserId,
    tickers: str | None = Query(None, description="Comma-separated ticker symbols"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, description="Pagination cursor"),
    published_after: str | None = Query(None, description="ISO 8601 date filter"),
    published_before: str | None = Query(None, description="ISO 8601 date filter"),
    order: str | None = Query(None, description="Sort order: asc or desc"),
    sort: str | None = Query(None, description="Sort field, e.g. published_utc"),
    market: Optional[str] = Query(
        None, description="Market filter: 'us' or 'cn'. Filters articles by ticker suffix."
    ),
) -> NewsCompactResponse:
    market = validate_market(market)
    ticker_list = (
        [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if tickers
        else None
    )

    # Check cache (skip when cursor is used — paginated requests bypass cache)
    if not cursor:
        cached = await _cache.get(tickers=ticker_list, limit=limit, market=market)
        if cached:
            results = [c for a in cached["results"] if (c := _compact(a)) is not None]
            return NewsCompactResponse(
                results=results,
                count=len(results),
                next_cursor=cached.get("next_cursor"),
            )

    from src.data_client import get_news_data_provider

    provider = await get_news_data_provider()
    data = await provider.get_news(
        tickers=ticker_list,
        limit=limit,
        cursor=cursor,
        published_after=published_after,
        published_before=published_before,
        order=order,
        sort=sort,
        user_id=user_id,
    )

    # Filter by market BEFORE applying limit / returning results
    if market:
        data["results"] = _filter_by_market(data["results"], market)

    # Populate cache (stores full articles internally)
    if not cursor:
        await _cache.set(data, tickers=ticker_list, limit=limit, market=market)

    results = [c for a in data["results"] if (c := _compact(a)) is not None]
    return NewsCompactResponse(
        results=results,
        count=len(results),
        next_cursor=data.get("next_cursor"),
    )


@router.get("/{article_id}", response_model=NewsArticle)
async def get_news_article(article_id: str, user_id: CurrentUserId):
    # Fast path: check cache
    cached = await _cache.get_article_by_id(article_id)
    if cached:
        return NewsArticle(**cached)

    # Slow path: fetch from provider chain
    from src.data_client import get_news_data_provider

    provider = await get_news_data_provider()
    article = await provider.get_news_article(article_id, user_id=user_id)
    if article:
        return NewsArticle(**article)

    raise HTTPException(status_code=404, detail="Article not found")
