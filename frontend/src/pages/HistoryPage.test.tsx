import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HistoryPage from './HistoryPage';
import type { ConversationData } from '../lib/storage';

const conversations = new Map<string, ConversationData>();

vi.mock('../lib/storage', () => ({
  getAllConversationIds: vi.fn(async () => [...conversations.keys()]),
  getConversation: vi.fn(async (id: string) => conversations.get(id)),
  saveWord: vi.fn(async () => {}),
}));

const sampleA: ConversationData = {
  sessionId: 'a',
  personaId: 'p',
  personaName: 'Tilly',
  turns: [],
  createdAt: 2000,
  updatedAt: 2000,
  summary: {
    newWords: [{ word: 'cup', definition: '', example: '' }],
    grammarPoints: ['present tense'],
    fluencyScore: 8,
    strengths: ['vocab'],
    areasToImprove: [],
  },
};

const sampleB: ConversationData = {
  sessionId: 'b',
  personaId: 'p',
  personaName: 'Ollie',
  turns: [{ userMessage: 'hi', assistantResponse: { speak: 'hi', learning: '', followup: '' }, timestamp: 1 }],
  createdAt: 1000,
  updatedAt: 1000,
};

beforeEach(() => {
  conversations.clear();
  vi.clearAllMocks();
});

describe('HistoryPage', () => {
  it('renders empty state when no conversations exist', async () => {
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText(/No past sessions/i)).toBeInTheDocument();
    });
  });

  it('renders conversations sorted newest first', async () => {
    conversations.set('a', sampleA);
    conversations.set('b', sampleB);
    render(<HistoryPage />);
    const items = await screen.findAllByRole('button');
    // First listed should be Tilly (created at 2000)
    expect(items[0]).toHaveTextContent('Tilly');
    expect(items[1]).toHaveTextContent('Ollie');
  });

  it('shows fluency score chip when summary exists', async () => {
    conversations.set('a', sampleA);
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText(/Score 8/)).toBeInTheDocument();
    });
  });

  it('opens summary modal when row clicked', async () => {
    conversations.set('a', sampleA);
    render(<HistoryPage />);
    const row = await screen.findByRole('button', { name: /Tilly/ });
    fireEvent.click(row);
    expect(await screen.findByRole('dialog', { name: /summary/i })).toBeInTheDocument();
  });

  it('shows fallback modal when conversation has no summary', async () => {
    conversations.set('b', sampleB);
    render(<HistoryPage />);
    const row = await screen.findByRole('button', { name: /Ollie/ });
    fireEvent.click(row);
    expect(await screen.findByRole('dialog', { name: /Session details/i })).toBeInTheDocument();
  });
});
