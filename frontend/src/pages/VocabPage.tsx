import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getAllWords,
  getDueWords,
  updateWordSchedule,
  type VocabRecord,
} from '../lib/storage';
import { nextSchedule, type ReviewQuality } from '../lib/srs';

type Tab = 'all' | 'review';

function formatDue(now: number, dueAt: number): string {
  const diff = dueAt - now;
  if (diff <= 0) return 'due';
  const days = Math.round(diff / (24 * 60 * 60 * 1000));
  if (days === 0) return 'today';
  if (days === 1) return 'in 1 day';
  return `in ${days} days`;
}

export default function VocabPage() {
  const [tab, setTab] = useState<Tab>('all');
  const [allWords, setAllWords] = useState<VocabRecord[]>([]);
  const [dueWords, setDueWords] = useState<VocabRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewIndex, setReviewIndex] = useState(0);
  const [revealAnswer, setRevealAnswer] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [all, due] = await Promise.all([getAllWords(), getDueWords(Date.now())]);
      setAllWords(all.sort((a, b) => b.addedAt - a.addedAt));
      setDueWords(due);
      setReviewIndex(0);
      setRevealAnswer(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const currentCard = useMemo(() => dueWords[reviewIndex], [dueWords, reviewIndex]);

  async function handleGrade(quality: ReviewQuality) {
    if (!currentCard) return;
    const sched = nextSchedule(currentCard, quality);
    await updateWordSchedule(currentCard.word, sched);

    if (reviewIndex + 1 >= dueWords.length) {
      // Re-fetch to reflect updates
      await refresh();
      setTab('all');
    } else {
      setReviewIndex(reviewIndex + 1);
      setRevealAnswer(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Vocabulary</h1>
          <a href="#/" className="text-sm text-indigo-600 hover:underline">
            ← Home
          </a>
        </div>

        <div role="tablist" className="mb-4 inline-flex overflow-hidden rounded-lg border border-slate-300 bg-white">
          <button
            role="tab"
            type="button"
            aria-selected={tab === 'all'}
            onClick={() => setTab('all')}
            className={
              tab === 'all'
                ? 'bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white'
                : 'bg-white px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50'
            }
          >
            All words ({allWords.length})
          </button>
          <button
            role="tab"
            type="button"
            aria-selected={tab === 'review'}
            onClick={() => setTab('review')}
            className={
              tab === 'review'
                ? 'bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white'
                : 'bg-white px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50'
            }
          >
            Review ({dueWords.length})
          </button>
        </div>

        {loading && <p className="text-sm text-slate-500">Loading…</p>}

        {!loading && tab === 'all' && allWords.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
            No words yet. Finish a chat session to collect vocabulary!
          </p>
        )}

        {!loading && tab === 'all' && allWords.length > 0 && (
          <ul className="space-y-2">
            {allWords.map((w) => (
              <li
                key={w.word}
                className="rounded-lg border border-slate-200 bg-white px-4 py-3"
              >
                <div className="flex items-baseline justify-between">
                  <p className="font-semibold text-slate-900">{w.word}</p>
                  <span className="text-xs text-slate-400">{formatDue(Date.now(), w.dueAt)}</span>
                </div>
                {w.definition && <p className="mt-1 text-sm text-slate-600">{w.definition}</p>}
                {w.example && <p className="mt-1 text-sm italic text-slate-500">"{w.example}"</p>}
              </li>
            ))}
          </ul>
        )}

        {!loading && tab === 'review' && dueWords.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
            Nothing due. Come back tomorrow!
          </p>
        )}

        {!loading && tab === 'review' && currentCard && (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-xs text-slate-400">
              Card {reviewIndex + 1} of {dueWords.length}
            </p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{currentCard.word}</p>

            {!revealAnswer && (
              <button
                type="button"
                onClick={() => setRevealAnswer(true)}
                className="mt-6 w-full rounded-lg bg-slate-100 px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-200"
              >
                Show answer
              </button>
            )}

            {revealAnswer && (
              <>
                {currentCard.definition && (
                  <p className="mt-4 text-sm text-slate-700">{currentCard.definition}</p>
                )}
                {currentCard.example && (
                  <p className="mt-2 text-sm italic text-slate-500">"{currentCard.example}"</p>
                )}
                <div className="mt-6 grid grid-cols-4 gap-2">
                  <button
                    type="button"
                    onClick={() => handleGrade(1)}
                    className="rounded-lg bg-rose-500 px-3 py-2 text-sm font-medium text-white hover:bg-rose-600"
                  >
                    Again
                  </button>
                  <button
                    type="button"
                    onClick={() => handleGrade(2)}
                    className="rounded-lg bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600"
                  >
                    Hard
                  </button>
                  <button
                    type="button"
                    onClick={() => handleGrade(3)}
                    className="rounded-lg bg-sky-500 px-3 py-2 text-sm font-medium text-white hover:bg-sky-600"
                  >
                    Good
                  </button>
                  <button
                    type="button"
                    onClick={() => handleGrade(4)}
                    className="rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600"
                  >
                    Easy
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
