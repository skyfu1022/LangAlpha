"""Composite provider for fundamental + market intelligence data."""

from __future__ import annotations

import logging
from typing import Any

from .base import FinancialDataSource, MarketIntelSource

logger = logging.getLogger(__name__)


class FallbackFinancialDataSource:
    """Try multiple financial sources in order until one succeeds."""

    def __init__(self, sources: list[FinancialDataSource]) -> None:
        self._sources = [source for source in sources if source is not None]

    def __getattr__(self, name: str) -> Any:
        async def _call(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for source in self._sources:
                method = getattr(source, name)
                try:
                    return await method(*args, **kwargs)
                except Exception as exc:
                    logger.warning(
                        "financial_data.fallback | method=%s source=%s error=%s",
                        name,
                        type(source).__name__,
                        exc,
                    )
                    last_exc = exc
            if last_exc is not None:
                raise last_exc
            raise AttributeError(name)

        return _call

    async def close(self) -> None:
        for source in self._sources:
            await source.close()


class FinancialDataProvider:
    """Bundles a :class:`FinancialDataSource` and a :class:`MarketIntelSource`.

    Either source may be ``None`` if the backing service is unavailable.
    """

    def __init__(
        self,
        financial: FinancialDataSource | tuple[FinancialDataSource, ...] | list[FinancialDataSource] | None = None,
        intel: MarketIntelSource | None = None,
    ) -> None:
        if isinstance(financial, (tuple, list)):
            financial = FallbackFinancialDataSource(list(financial)) if financial else None
        self.financial = financial
        self.intel = intel

    async def close(self) -> None:
        if self.financial is not None:
            await self.financial.close()
        if self.intel is not None:
            await self.intel.close()
