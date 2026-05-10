import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import LevelSelector from '../components/LevelSelector';

describe('LevelSelector', () => {
  it('renders three level buttons', () => {
    render(<LevelSelector value="beginner" onChange={() => {}} />);
    expect(screen.getByRole('radio', { name: /beginner/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /intermediate/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /advanced/i })).toBeInTheDocument();
  });

  it('marks the current value as checked', () => {
    render(<LevelSelector value="advanced" onChange={() => {}} />);
    const btn = screen.getByRole('radio', { name: /advanced/i });
    expect(btn).toHaveAttribute('aria-checked', 'true');
  });

  it('calls onChange when clicking a different level', () => {
    const onChange = vi.fn();
    render(<LevelSelector value="beginner" onChange={onChange} />);
    fireEvent.click(screen.getByRole('radio', { name: /intermediate/i }));
    expect(onChange).toHaveBeenCalledWith('intermediate');
  });
});
