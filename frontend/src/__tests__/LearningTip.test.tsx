import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import LearningTip from '../components/LearningTip';

describe('LearningTip', () => {
  it('renders nothing when both learning and followup are empty', () => {
    const { container } = render(<LearningTip learning="" followup="" />);
    expect(container.innerHTML).toBe('');
  });

  it('displays collapsed by default', () => {
    render(<LearningTip learning="New word: teacup" followup="Try saying it!" />);
    expect(screen.getByText(/Learning Tip/)).toBeInTheDocument();
    expect(screen.queryByText(/New word/)).not.toBeInTheDocument();
  });

  it('expands on click', () => {
    render(<LearningTip learning="New word: teacup" followup="Try saying it!" />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/New word/)).toBeInTheDocument();
    expect(screen.getByText(/Try saying it/)).toBeInTheDocument();
  });

  it('toggles collapse on second click', () => {
    render(<LearningTip learning="vocab word" followup="practice question" />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/vocab word/)).toBeInTheDocument();
    expect(screen.getByText(/practice question/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText(/vocab word/)).not.toBeInTheDocument();
  });
});
