"""Market region validation utilities."""

from fastapi import HTTPException

VALID_MARKETS = ("us", "cn")


def validate_market(market: str | None) -> str:
    """Normalize and validate market parameter.

    Returns the normalized market string ('us' or 'cn').
    Raises HTTPException 400 if the value is invalid.
    """
    if market is None:
        return "us"
    m = market.lower().strip()
    if m not in VALID_MARKETS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid market: {market!r}. Must be 'us' or 'cn'.",
        )
    return m
