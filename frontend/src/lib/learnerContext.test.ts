import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { VocabRecord, ConversationData } from './storage';

const words: VocabRecord[] = [];
const ids: string[] = [];
const conversations = new Map<string, ConversationData>();

vi.mock('./storage', () => ({
  getAllWords: vi.fn(async () => [...words]),
  getAllConversationIds: vi.fn(async () => [...ids]),
  getConversation: vi.fn(async (id: string) => conversations.get(id)),
}));

beforeEach(() => {
  words.length = 0;
  ids.length = 0;
  conversations.clear();
});

import { collectLearnerContext } from './learnerContext';

function makeWord(word: string, addedAt: number): VocabRecord {
  return {
    word,
    definition: '',
    example: '',
    sessionId: 's',
    addedAt,
    dueAt: addedAt,
    ease: 2.5,
    intervalDays: 0,
    reps: 0,
  };
}

describe('collectLearnerContext', () => {
  it('returns empty arrays when DB is empty', async () => {
    const ctx = await collectLearnerContext('beginner');
    expect(ctx).toEqual({ level: 'beginner', recent_vocab: [], weak_areas: [] });
  });

  it('returns the most recent 20 words by addedAt desc', async () => {
    for (let i = 0; i < 30; i++) {
      words.push(makeWord(`w${i}`, i));
    }
    const ctx = await collectLearnerContext('intermediate');
    expect(ctx.recent_vocab).toHaveLength(20);
    expect(ctx.recent_vocab[0]).toBe('w29');
    expect(ctx.recent_vocab[19]).toBe('w10');
  });

  it('picks weak_areas from the most-recent summary', async () => {
    ids.push('a', 'b');
    conversations.set('a', {
      sessionId: 'a',
      personaId: 'p',
      personaName: 'A',
      turns: [],
      createdAt: 1,
      updatedAt: 10,
      summary: {
        newWords: [],
        grammarPoints: [],
        fluencyScore: 5,
        strengths: [],
        areasToImprove: ['old area'],
      },
    });
    conversations.set('b', {
      sessionId: 'b',
      personaId: 'p',
      personaName: 'B',
      turns: [],
      createdAt: 2,
      updatedAt: 20,
      summary: {
        newWords: [],
        grammarPoints: [],
        fluencyScore: 5,
        strengths: [],
        areasToImprove: ['recent area'],
      },
    });
    const ctx = await collectLearnerContext('advanced');
    expect(ctx.weak_areas).toEqual(['recent area']);
  });

  it('skips conversations that have no summary', async () => {
    ids.push('a');
    conversations.set('a', {
      sessionId: 'a',
      personaId: 'p',
      personaName: 'A',
      turns: [],
      createdAt: 1,
      updatedAt: 10,
    });
    const ctx = await collectLearnerContext('beginner');
    expect(ctx.weak_areas).toEqual([]);
  });
});
