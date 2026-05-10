import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SummaryCard from '../components/SummaryCard';
import type { SummaryData } from '../components/SummaryCard';

const fullSummary: SummaryData = {
  newWords: ['teacup', 'saucer', 'brew'],
  grammarPoints: ['Present simple tense'],
  fluencyScore: 8,
  strengths: ['Good vocabulary', 'Clear pronunciation'],
  areasToImprove: ['Past tense usage'],
};

const emptySummary: SummaryData = {
  newWords: [],
  grammarPoints: [],
  fluencyScore: 5,
  strengths: [],
  areasToImprove: [],
};

describe('SummaryCard', () => {
  it('renders fluency score', () => {
    render(<SummaryCard summary={fullSummary} personaName="Tilly" />);
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText(/Fluency Score/)).toBeInTheDocument();
  });

  it('renders persona name', () => {
    render(<SummaryCard summary={fullSummary} personaName="Tilly" />);
    expect(screen.getByText(/Tilly/)).toBeInTheDocument();
  });

  it('renders new words as chips', () => {
    render(<SummaryCard summary={fullSummary} personaName="Tilly" />);
    expect(screen.getByText('teacup')).toBeInTheDocument();
    expect(screen.getByText('saucer')).toBeInTheDocument();
    expect(screen.getByText('brew')).toBeInTheDocument();
  });

  it('renders grammar points', () => {
    render(<SummaryCard summary={fullSummary} personaName="Tilly" />);
    expect(screen.getByText('Present simple tense')).toBeInTheDocument();
  });

  it('renders strengths and areas to improve', () => {
    render(<SummaryCard summary={fullSummary} personaName="Tilly" />);
    expect(screen.getByText(/Good vocabulary/)).toBeInTheDocument();
    expect(screen.getByText(/Past tense/)).toBeInTheDocument();
  });

  it('shows empty state when no data', () => {
    render(<SummaryCard summary={emptySummary} personaName="Bot" />);
    expect(screen.getByText(/No learning data/)).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(<SummaryCard summary={fullSummary} personaName="Tilly" onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onPracticeAgain when button clicked', () => {
    const onPracticeAgain = vi.fn();
    render(
      <SummaryCard summary={fullSummary} personaName="Tilly" onPracticeAgain={onPracticeAgain} />
    );
    fireEvent.click(screen.getByRole('button', { name: /practice/i }));
    expect(onPracticeAgain).toHaveBeenCalled();
  });

  it('score 1-3 shows red styling', () => {
    const low: SummaryData = { ...fullSummary, fluencyScore: 2 };
    const { container } = render(<SummaryCard summary={low} personaName="Tilly" />);
    const scoreBadge = container.querySelector('.flex.h-20');
    expect(scoreBadge).toBeInTheDocument();
  });

  it('score 7-10 shows green styling', () => {
    const high: SummaryData = { ...fullSummary, fluencyScore: 9 };
    const { container } = render(<SummaryCard summary={high} personaName="Tilly" />);
    const scoreBadge = container.querySelector('.flex.h-20');
    expect(scoreBadge).toBeInTheDocument();
  });
});
