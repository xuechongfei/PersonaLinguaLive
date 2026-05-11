import { getAllWords, getAllConversationIds, getConversation } from './storage';

export interface LearnerContext {
  level: string;
  recent_vocab: string[];
  weak_areas: string[];
}

const VOCAB_CAP = 20;

export async function collectLearnerContext(level: string): Promise<LearnerContext> {
  const [words, ids] = await Promise.all([getAllWords(), getAllConversationIds()]);

  const recent_vocab = [...words]
    .sort((a, b) => b.addedAt - a.addedAt)
    .slice(0, VOCAB_CAP)
    .map((w) => w.word);

  let weak_areas: string[] = [];
  if (ids.length > 0) {
    const convos = await Promise.all(ids.map((id) => getConversation(id)));
    const latest = convos
      .filter((c): c is NonNullable<typeof c> => Boolean(c?.summary))
      .sort((a, b) => b.updatedAt - a.updatedAt)[0];
    if (latest?.summary?.areasToImprove) {
      weak_areas = latest.summary.areasToImprove;
    }
  }

  return { level, recent_vocab, weak_areas };
}
