import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useMarket } from '../useMarket';
import i18n from '@/i18n';

const storage = window.localStorage;

describe('useMarket', () => {
  beforeEach(() => {
    storage.removeItem('langalpha-market');
    storage.removeItem('locale');
    void i18n.changeLanguage('en-US');
  });

  it('returns "us" by default when no stored value', () => {
    const { result } = renderHook(() => useMarket());
    expect(result.current.market).toBe('us');
    expect(result.current.config.label).toBe('US');
  });

  it('returns stored market from localStorage', async () => {
    storage.setItem('langalpha-market', 'cn');
    const { result } = renderHook(() => useMarket());
    expect(result.current.market).toBe('cn');
    expect(result.current.config.label).toBe('CN');
    await waitFor(() => {
      expect(storage.getItem('locale')).toBe('zh-CN');
    });
  });

  it('switches market and persists to localStorage', async () => {
    const { result } = renderHook(() => useMarket());
    expect(result.current.market).toBe('us');

    act(() => {
      result.current.switchMarket('cn');
    });

    expect(result.current.market).toBe('cn');
    expect(storage.getItem('langalpha-market')).toBe('cn');
    await waitFor(() => {
      expect(storage.getItem('locale')).toBe('zh-CN');
    });
    expect(result.current.config.indices[0].name).toBe('上证指数');
  });

  it('ignores invalid stored values', () => {
    storage.setItem('langalpha-market', 'invalid');
    const { result } = renderHook(() => useMarket());
    expect(result.current.market).toBe('us');
  });

  it('provides correct config for each market', () => {
    const { result } = renderHook(() => useMarket());

    // US config
    expect(result.current.config.indices.length).toBeGreaterThan(0);
    expect(result.current.config.defaultWatchlist.length).toBeGreaterThan(0);
    expect(result.current.config.defaultChartSymbol).toBe('GOOGL');

    act(() => result.current.switchMarket('cn'));

    // CN config
    expect(result.current.config.indices.length).toBe(4);
    expect(result.current.config.defaultWatchlist.length).toBe(5);
    expect(result.current.config.defaultChartSymbol).toBe('600519.SH');
  });
});
