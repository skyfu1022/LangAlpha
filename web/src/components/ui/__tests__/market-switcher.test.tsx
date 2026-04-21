import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MarketSwitcher } from '../market-switcher';

describe('MarketSwitcher', () => {
  it('renders US and CN buttons', () => {
    render(<MarketSwitcher market="us" onSwitch={vi.fn()} />);
    expect(screen.getByText('US')).toBeInTheDocument();
    expect(screen.getByText('CN')).toBeInTheDocument();
  });

  it('highlights active market', () => {
    render(<MarketSwitcher market="cn" onSwitch={vi.fn()} />);
    const cnBtn = screen.getByText('CN');
    expect(cnBtn.style.backgroundColor).toBeTruthy();
  });

  it('calls onSwitch when clicking inactive market', () => {
    const onSwitch = vi.fn();
    render(<MarketSwitcher market="us" onSwitch={onSwitch} />);
    fireEvent.click(screen.getByText('CN'));
    expect(onSwitch).toHaveBeenCalledWith('cn');
  });

  it('does not call onSwitch when clicking active market', () => {
    const onSwitch = vi.fn();
    render(<MarketSwitcher market="us" onSwitch={onSwitch} />);
    fireEvent.click(screen.getByText('US'));
    expect(onSwitch).not.toHaveBeenCalled();
  });
});
