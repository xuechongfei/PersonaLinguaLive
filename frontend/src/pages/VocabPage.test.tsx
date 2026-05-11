import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import VocabPage from './VocabPage';
import type { VocabRecord } from '../lib/storage';

const words = new Map<string, VocabRecord>();

vi.mock('../lib/storage', () => ({
  getAllWords: vi.fn(async () =>
    [...words.values()].sort((a, b) => b.addedAt - a.addedAt),
  ),
  getDueWords: vi.fn(async (now: number) =>
    [...words.values()].filter((w) => w.dueAt <= now),
  ),
  updateWordSchedule: vi.fn(async (word: string, updates: any) => {
    const w = words.get(word);
    if (w) words.set(word, { ...w, ...updates });
  }),
}));

const sample = (overrides: Partial<VocabRecord> = {}): VocabRecord => ({
  word: 'teacup',
  definition: 'a small cup for tea',
  example: 'Pour tea into the teacup.',
  sessionId: 's1',
  addedAt: Date.now(),
  dueAt: Date.now(),
  ease: 2.5,
  intervalDays: 0,
  reps: 0,
  ...overrides,
});

beforeEach(() => {
  words.clear();
  vi.clearAllMocks();
});

describe('VocabPage', () => {
  it('shows empty state when no words exist', async () => {
    render(<VocabPage />);
    await waitFor(() => {
      expect(screen.getByText(/No words yet/i)).toBeInTheDocument();
    });
  });

  it('lists all stored words on the All tab', async () => {
    words.set('teacup', sample());
    words.set('brew', sample({ word: 'brew', addedAt: 1 }));
    render(<VocabPage />);
    await waitFor(() => {
      expect(screen.getByText('teacup')).toBeInTheDocument();
      expect(screen.getByText('brew')).toBeInTheDocument();
    });
  });

  it('Review tab shows due cards and grading buttons', async () => {
    words.set('teacup', sample());
    render(<VocabPage />);
    await waitFor(() => screen.getByRole('tab', { name: /Review/i }));
    fireEvent.click(screen.getByRole('tab', { name: /Review/i }));

    expect(await screen.findByText('teacup')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Show answer/i }));
    expect(screen.getByRole('button', { name: /Easy/i })).toBeInTheDocument();
  });

  it('grading a card persists the schedule update', async () => {
    words.set('teacup', sample());
    render(<VocabPage />);
    fireEvent.click(await screen.findByRole('tab', { name: /Review/i }));
    fireEvent.click(await screen.findByRole('button', { name: /Show answer/i }));
    fireEvent.click(screen.getByRole('button', { name: /Easy/i }));

    const { updateWordSchedule } = await import('../lib/storage');
    await waitFor(() => {
      expect(updateWordSchedule).toHaveBeenCalledWith(
        'teacup',
        expect.objectContaining({ reps: 1 }),
      );
    });
  });
});
