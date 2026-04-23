import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { MarketOverviewItem } from '@/types/market';

// ── Mocks ──

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock framer-motion to render children without animation
vi.mock('framer-motion', () => ({
  motion: {
    div: ({
      children,
      onClick,
      onMouseEnter,
      onMouseLeave,
      ...rest
    }: React.HTMLAttributes<HTMLDivElement> & { initial?: unknown; animate?: unknown; transition?: unknown }) => (
      <div onClick={onClick} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave} {...rest}>
        {children}
      </div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock recharts to avoid rendering SVG in jsdom
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

// Mock useIsMobile to test desktop layout (so individual cards render)
vi.mock('@/hooks/useIsMobile', () => ({
  useIsMobile: () => false,
}));

// Mock react-i18next to return keys as values (no i18n init in test)
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        'dashboard.indexMovement.etfBadge': 'ETF',
        'dashboard.indexMovement.noChartData': 'No chart data',
      };
      return map[key] ?? key;
    },
    i18n: { language: 'en-US' },
  }),
}));

// ── Helpers ──

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function makeIndexItem(overrides: Partial<MarketOverviewItem> = {}): MarketOverviewItem {
  return {
    symbol: 'GSPC',
    name: 'S&P 500',
    price: 5500.42,
    change: 25.3,
    changePercent: 0.46,
    isPositive: true,
    sparklineData: [],
    assetType: 'index',
    ...overrides,
  };
}

function renderWithProviders(ui: React.ReactNode) {
  const qc = createQueryClient();
  return render(
    <QueryClientProvider client={qc}>{ui}</QueryClientProvider>,
  );
}

// ── Tests ──

describe('IndexMovementCard – market switching', () => {
  // Dynamically import so mocks are in place before module evaluation
  let IndexMovementCard: typeof import('../IndexMovementCard').default;

  beforeEach(async () => {
    vi.clearAllMocks();
    // Re-import to pick up fresh mocks
    const mod = await import('../IndexMovementCard');
    IndexMovementCard = mod.default;
  });

  it('renders index card with ^ prefix on symbol label', () => {
    const index = makeIndexItem({ symbol: 'GSPC', assetType: 'index' });
    renderWithProviders(<IndexMovementCard indices={[index]} />);

    expect(screen.getByText('^GSPC')).toBeInTheDocument();
    expect(screen.queryByText('ETF')).not.toBeInTheDocument();
  });

  it('renders ETF card with plain symbol (no ^ prefix)', () => {
    const etf = makeIndexItem({
      symbol: 'SPY',
      name: 'S&P 500 ETF',
      assetType: 'etf',
    });
    renderWithProviders(<IndexMovementCard indices={[etf]} />);

    // Symbol should be displayed without ^ prefix
    expect(screen.getByText('SPY')).toBeInTheDocument();
    // ^SPY should NOT be present
    expect(screen.queryByText('^SPY')).not.toBeInTheDocument();
  });

  it('renders ETF badge for etf assetType', () => {
    const etf = makeIndexItem({
      symbol: 'SPY',
      name: 'S&P 500 ETF',
      assetType: 'etf',
    });
    renderWithProviders(<IndexMovementCard indices={[etf]} />);

    expect(screen.getByText('ETF')).toBeInTheDocument();
  });

  it('does NOT render ETF badge for index assetType', () => {
    const index = makeIndexItem({ symbol: 'GSPC', assetType: 'index' });
    renderWithProviders(<IndexMovementCard indices={[index]} />);

    expect(screen.queryByText('ETF')).not.toBeInTheDocument();
  });

  it('renders CN index with exchange suffix as symbol label', () => {
    const cnIndex = makeIndexItem({
      symbol: '000001.SH',
      name: '上证指数',
      assetType: 'index',
    });
    renderWithProviders(<IndexMovementCard indices={[cnIndex]} />);

    // Index type gets ^ prefix
    expect(screen.getByText('^000001.SH')).toBeInTheDocument();
  });

  it('renders CN ETF with plain symbol and ETF badge', () => {
    const cnEtf = makeIndexItem({
      symbol: '510300.SH',
      name: '沪深300ETF',
      assetType: 'etf',
    });
    renderWithProviders(<IndexMovementCard indices={[cnEtf]} />);

    expect(screen.getByText('510300.SH')).toBeInTheDocument();
    expect(screen.getByText('ETF')).toBeInTheDocument();
  });

  it('renders multiple cards in desktop grid', () => {
    const indices = [
      makeIndexItem({ symbol: 'GSPC', name: 'S&P 500', assetType: 'index' }),
      makeIndexItem({ symbol: 'SPY', name: 'S&P 500 ETF', assetType: 'etf' }),
      makeIndexItem({ symbol: '510300.SH', name: '沪深300ETF', assetType: 'etf' }),
    ];
    renderWithProviders(<IndexMovementCard indices={indices} />);

    expect(screen.getByText('^GSPC')).toBeInTheDocument();
    expect(screen.getByText('SPY')).toBeInTheDocument();
    expect(screen.getByText('510300.SH')).toBeInTheDocument();
    // Two ETFs, one index => two ETF badges
    const etfBadges = screen.getAllByText('ETF');
    expect(etfBadges).toHaveLength(2);
  });

  it('renders nothing when indices is empty', () => {
    const { container } = renderWithProviders(<IndexMovementCard indices={[]} />);
    // Desktop grid exists but has no card children with text content
    expect(container.textContent).toBe('');
  });

  it('shows index name and price', () => {
    const index = makeIndexItem({
      symbol: 'GSPC',
      name: 'S&P 500',
      price: 5500.42,
      assetType: 'index',
    });
    renderWithProviders(<IndexMovementCard indices={[index]} />);

    expect(screen.getByText('S&P 500')).toBeInTheDocument();
    expect(screen.getByText('5,500.42')).toBeInTheDocument();
  });
});
