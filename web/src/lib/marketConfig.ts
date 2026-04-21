/**
 * Market configuration constants for US and CN (A-share) markets.
 *
 * Each market defines its index symbols, default watchlist, and display names.
 * The market switcher in Dashboard/MarketView toggles between these configs.
 */

export type MarketRegion = 'us' | 'cn';

export interface IndexEntry {
  symbol: string;
  name: string;
}

export interface MarketConfig {
  label: string;
  indices: IndexEntry[];
  defaultWatchlist: string[];
  defaultWatchlistNames: Record<string, string>;
  defaultChartSymbol: string;
}

export const MARKET_CONFIG: Record<MarketRegion, MarketConfig> = {
  us: {
    label: 'US',
    indices: [
      { symbol: 'GSPC', name: 'S&P 500' },
      { symbol: 'IXIC', name: 'NASDAQ' },
      { symbol: 'DJI', name: 'Dow Jones' },
      { symbol: 'RUT', name: 'Russell 2000' },
      { symbol: 'VIX', name: 'VIX' },
    ],
    defaultWatchlist: ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'TSLA'],
    defaultWatchlistNames: {
      AAPL: 'Apple',
      MSFT: 'Microsoft',
      NVDA: 'NVIDIA',
      AMZN: 'Amazon',
      TSLA: 'Tesla',
    },
    defaultChartSymbol: 'GOOGL',
  },
  cn: {
    label: 'CN',
    indices: [
      { symbol: '000001.SH', name: '上证指数' },
      { symbol: '399001.SZ', name: '深证成指' },
      { symbol: '399006.SZ', name: '创业板指' },
      { symbol: '000300.SH', name: '沪深300' },
    ],
    defaultWatchlist: ['600519.SH', '000858.SZ', '601318.SH', '600036.SH', '000001.SZ'],
    defaultWatchlistNames: {
      '600519.SH': '贵州茅台',
      '000858.SZ': '五粮液',
      '601318.SH': '中国平安',
      '600036.SH': '招商银行',
      '000001.SZ': '平安银行',
    },
    defaultChartSymbol: '600519.SH',
  },
};
