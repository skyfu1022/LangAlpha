import { MARKET_CONFIG, type MarketRegion } from '@/lib/marketConfig';

interface MarketSwitcherProps {
  market: MarketRegion;
  onSwitch: (market: MarketRegion) => void;
}

export function MarketSwitcher({ market, onSwitch }: MarketSwitcherProps) {
  return (
    <div
      className="flex items-center rounded-lg p-0.5 gap-0.5"
      style={{
        backgroundColor: 'var(--color-bg-input)',
        border: '1px solid var(--color-border-muted)',
      }}
    >
      {(Object.keys(MARKET_CONFIG) as MarketRegion[]).map((key) => (
        <button
          key={key}
          onClick={() => { if (market !== key) onSwitch(key); }}
          className="px-2.5 py-1 text-xs font-medium rounded-md transition-all"
          style={{
            backgroundColor: market === key ? 'var(--color-accent-primary)' : 'transparent',
            color: market === key ? '#fff' : 'var(--color-text-secondary)',
            cursor: market === key ? 'default' : 'pointer',
          }}
          onMouseEnter={(e) => {
            if (market !== key) e.currentTarget.style.color = 'var(--color-text-primary)';
          }}
          onMouseLeave={(e) => {
            if (market !== key) e.currentTarget.style.color = 'var(--color-text-secondary)';
          }}
        >
          {MARKET_CONFIG[key].label}
        </button>
      ))}
    </div>
  );
}
