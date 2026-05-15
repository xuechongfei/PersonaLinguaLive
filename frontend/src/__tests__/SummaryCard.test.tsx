import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SummaryCard from '../components/SummaryCard';
import type { SummaryData } from '../components/SummaryCard';

vi.mock('../lib/storage', () => ({
  saveWord: vi.fn(async () => {}),
}));

const fullSummary: SummaryData = {
  newWords: [
    { word: 'teacup', definition: 'small tea cup', example: 'Use a teacup.' },
    { word: 'saucer', definition: 'plate under a cup', example: '' },
    { word: 'brew', definition: 'to make tea', example: '' },
  ],
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
    expect(screen.getByText('Great Job')).toBeInTheDocument();
  });

  it('renders persona name', () => {
    render(<SummaryCard summary={fullSummary} personaName="Tilly" />);
    const tillyMatches = screen.getAllByText(/Tilly/);
    expect(tillyMatches.length).toBeGreaterThanOrEqual(1);
  });

  it('renders new words', () => {
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
    render(<SummaryCard summary={fullSummary} personaName="Tilly" onPracticeAgain={onPracticeAgain} />);
    fireEvent.click(screen.getByRole('button', { name: /practice/i }));
    expect(onPracticeAgain).toHaveBeenCalled();
  });

  it('low fluency shows keep going label', () => {
    const low: SummaryData = { ...fullSummary, fluencyScore: 2 };
    render(<SummaryCard summary={low} personaName="Tilly" />);
    expect(screen.getByText('Keep Going')).toBeInTheDocument();
  });

  it('high fluency shows great job label', () => {
    const high: SummaryData = { ...fullSummary, fluencyScore: 9 };
    render(<SummaryCard summary={high} personaName="Tilly" />);
    expect(screen.getByText('Great Job')).toBeInTheDocument();
  });
});
