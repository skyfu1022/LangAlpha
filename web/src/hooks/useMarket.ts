import { useState, useCallback } from 'react';
import { MARKET_CONFIG, type MarketRegion, type MarketConfig } from '@/lib/marketConfig';
import i18n from '@/i18n';

const STORAGE_KEY = 'langalpha-market';

const MARKET_TO_LOCALE: Record<MarketRegion, string> = {
  cn: 'zh-CN',
  us: 'en-US',
};

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
    if (i18n.language !== MARKET_TO_LOCALE[m]) {
      i18n.changeLanguage(MARKET_TO_LOCALE[m]);
    }
  }, []);

  const config: MarketConfig = MARKET_CONFIG[market];

  return { market, switchMarket, config };
}
