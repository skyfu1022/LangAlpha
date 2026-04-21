import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { renderHookWithProviders } from '@/test/utils';
import { useStockData } from '../useStockData';

vi.mock('../../utils/api', () => ({
  fetchStockQuote: vi.fn(),
  fetchCompanyOverview: vi.fn(),
  fetchAnalystData: vi.fn(),
}));

vi.mock('@/lib/marketUtils', () => ({
  fetchMarketStatus: vi.fn(),
}));

import {
  fetchStockQuote,
  fetchCompanyOverview,
  fetchAnalystData,
} from '../../utils/api';
import { fetchMarketStatus } from '@/lib/marketUtils';

describe('useStockData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchStockQuote).mockResolvedValue({
      stockInfo: null,
      realTimePrice: null,
      snapshot: null,
    });
    vi.mocked(fetchCompanyOverview).mockResolvedValue(null);
    vi.mocked(fetchAnalystData).mockResolvedValue(null);
    vi.mocked(fetchMarketStatus).mockResolvedValue(null);
  });

  it('does not fetch company overview or analyst data for index symbols', async () => {
    renderHookWithProviders(() =>
      useStockData({
        selectedStock: '^000001.SH',
        wsStatus: 'disconnected',
      })
    );

    await waitFor(() => {
      expect(fetchStockQuote).toHaveBeenCalledWith('^000001.SH', expect.any(Object));
    });

    expect(fetchCompanyOverview).not.toHaveBeenCalled();
    expect(fetchAnalystData).not.toHaveBeenCalled();
  });
});
