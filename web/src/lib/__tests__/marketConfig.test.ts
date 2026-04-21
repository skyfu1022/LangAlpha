import { describe, it, expect } from 'vitest';
import { MARKET_CONFIG, type MarketRegion } from '../marketConfig';

describe('marketConfig', () => {
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
    // All CN watchlist symbols should have exchange suffix
    cn.defaultWatchlist.forEach((s) => {
      expect(s).toMatch(/\.(SH|SZ)$/);
    });
  });

  it('cn default watchlist names map to correct symbols', () => {
    const cn = MARKET_CONFIG.cn;
    expect(cn.defaultWatchlistNames['600519.SH']).toBe('贵州茅台');
    expect(cn.defaultWatchlistNames['000858.SZ']).toBe('五粮液');
  });

  it('all markets have consistent structure', () => {
    (Object.keys(MARKET_CONFIG) as MarketRegion[]).forEach((key) => {
      const cfg = MARKET_CONFIG[key];
      expect(cfg).toHaveProperty('label');
      expect(cfg).toHaveProperty('indices');
      expect(cfg).toHaveProperty('defaultWatchlist');
      expect(cfg).toHaveProperty('defaultWatchlistNames');
      expect(cfg).toHaveProperty('defaultChartSymbol');
      expect(cfg.indices.length).toBeGreaterThan(0);
      expect(cfg.defaultWatchlist.length).toBeGreaterThan(0);
    });
  });
});
