import { useState, useCallback } from 'react';
import { MARKET_CONFIG, type MarketRegion, type MarketConfig } from '@/lib/marketConfig';

const STORAGE_KEY = 'langalpha-market';

export function useMarket() {
  const [market, setMarket] = useState<MarketRegion>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'us' || stored === 'cn') return stored;
    } catch { /* ignore */ }
    return 'us';
  });

  const switchMarket = useCallback((m: MarketRegion) => {
    setMarket(m);
    try { localStorage.setItem(STORAGE_KEY, m); } catch { /* ignore */ }
  }, []);

  const config: MarketConfig = MARKET_CONFIG[market];

  return { market, switchMarket, config };
}
