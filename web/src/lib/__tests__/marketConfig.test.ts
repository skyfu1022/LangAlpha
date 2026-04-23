import { describe, it, expect } from 'vitest';
import {
  getSymbolMarket,
  filterByMarket,
  MARKET_CONFIG,
  type MarketRegion,
} from '../marketConfig';

// ── getSymbolMarket ──

describe('getSymbolMarket', () => {
  it('returns cn for .SH suffix', () => {
    expect(getSymbolMarket('600519.SH')).toBe('cn');
  });

  it('returns cn for .SZ suffix', () => {
    expect(getSymbolMarket('000858.SZ')).toBe('cn');
  });

  it('returns cn for .SS suffix', () => {
    expect(getSymbolMarket('600000.SS')).toBe('cn');
  });

  it('returns cn regardless of case', () => {
    expect(getSymbolMarket('600519.sh')).toBe('cn');
    expect(getSymbolMarket('000858.sz')).toBe('cn');
  });

  it('returns us for bare symbols', () => {
    expect(getSymbolMarket('AAPL')).toBe('us');
  });

  it('returns us for unknown suffixes', () => {
    expect(getSymbolMarket('SAP.DE')).toBe('us');
  });

  it('returns cn for CN ETF symbols', () => {
    expect(getSymbolMarket('510300.SH')).toBe('cn');
    expect(getSymbolMarket('159919.SZ')).toBe('cn');
  });

  it('returns us for US ETF symbols', () => {
    expect(getSymbolMarket('SPY')).toBe('us');
    expect(getSymbolMarket('QQQ')).toBe('us');
  });
});

// ── filterByMarket ──

describe('filterByMarket', () => {
  const items = [
    { symbol: 'AAPL', name: 'Apple' },
    { symbol: '600519.SH', name: '贵州茅台' },
    { symbol: 'SPY', name: 'S&P 500 ETF' },
    { symbol: '510300.SH', name: '沪深300ETF' },
  ];

  it('filters for US market', () => {
    const result = filterByMarket(items, 'us');
    expect(result).toHaveLength(2);
    expect(result.map((r) => r.symbol)).toEqual(['AAPL', 'SPY']);
  });

  it('filters for CN market', () => {
    const result = filterByMarket(items, 'cn');
    expect(result).toHaveLength(2);
    expect(result.map((r) => r.symbol)).toEqual(['600519.SH', '510300.SH']);
  });

  it('returns empty for empty input', () => {
    expect(filterByMarket([], 'us')).toEqual([]);
  });

  it('preserves extra properties on items', () => {
    const enriched = [
      { symbol: 'AAPL', name: 'Apple', extra: 42 },
      { symbol: '600519.SH', name: '贵州茅台', extra: 99 },
    ];
    const us = filterByMarket(enriched, 'us');
    expect(us[0].extra).toBe(42);
  });
});

// ── MARKET_CONFIG structure ──

describe('MARKET_CONFIG', () => {
  it('has us and cn keys', () => {
    expect(Object.keys(MARKET_CONFIG)).toEqual(['us', 'cn']);
  });

  it('us market has expected indices', () => {
    const us = MARKET_CONFIG.us;
    expect(us.indices.map((i) => i.symbol)).toEqual(['GSPC', 'IXIC', 'DJI', 'RUT', 'VIX']);
    expect(us.defaultWatchlist).toContain('AAPL');
    expect(us.defaultChartSymbol).toBe('GOOGL');
  });

  it('cn market has expected A-share indices', () => {
    const cn = MARKET_CONFIG.cn;
    const symbols = cn.indices.map((i) => i.symbol);
    expect(symbols).toContain('000001.SH');
    expect(symbols).toContain('399001.SZ');
    expect(symbols).toContain('399006.SZ');
    expect(symbols).toContain('000300.SH');
  });

  it('cn default watchlist contains A-share stocks', () => {
    const cn = MARKET_CONFIG.cn;
    expect(cn.defaultWatchlist.length).toBe(5);
    cn.defaultWatchlist.forEach((s) => {
      expect(s).toMatch(/\.(SH|SZ)$/);
    });
  });

  it('cn default watchlist names map to correct symbols', () => {
    const cn = MARKET_CONFIG.cn;
    expect(cn.defaultWatchlistNames['600519.SH']).toBe('贵州茅台');
    expect(cn.defaultWatchlistNames['000858.SZ']).toBe('五粮液');
  });

  it('has currencySymbol for both markets', () => {
    expect(MARKET_CONFIG.us.currencySymbol).toBe('$');
    expect(MARKET_CONFIG.cn.currencySymbol).toBe('¥');
  });

  it('has ETFs for both markets', () => {
    expect(MARKET_CONFIG.us.etfs.length).toBeGreaterThan(0);
    expect(MARKET_CONFIG.cn.etfs.length).toBeGreaterThan(0);
  });

  it('us ETFs include major benchmark ETFs', () => {
    const symbols = MARKET_CONFIG.us.etfs.map((e) => e.symbol);
    expect(symbols).toContain('SPY');
    expect(symbols).toContain('QQQ');
  });

  it('cn ETFs include major benchmark ETFs', () => {
    const symbols = MARKET_CONFIG.cn.etfs.map((e) => e.symbol);
    expect(symbols).toContain('510300.SH');
  });

  it('all markets have consistent structure', () => {
    (Object.keys(MARKET_CONFIG) as MarketRegion[]).forEach((key) => {
      const cfg = MARKET_CONFIG[key];
      expect(cfg).toHaveProperty('label');
      expect(cfg).toHaveProperty('indices');
      expect(cfg).toHaveProperty('etfs');
      expect(cfg).toHaveProperty('defaultWatchlist');
      expect(cfg).toHaveProperty('defaultWatchlistNames');
      expect(cfg).toHaveProperty('defaultChartSymbol');
      expect(cfg).toHaveProperty('currencySymbol');
      expect(cfg.indices.length).toBeGreaterThan(0);
      expect(cfg.defaultWatchlist.length).toBeGreaterThan(0);
    });
  });
});
