import { useCallback, useEffect, useMemo, useState } from 'react';
import { getAllWords, getDueWords, updateWordSchedule, type VocabRecord } from '../lib/storage';
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

const GRADE_LABELS: { quality: ReviewQuality; label: string; className: string }[] = [
  { quality: 1, label: 'Again', className: 'bg-rose hover:bg-rose/90' },
  { quality: 2, label: 'Hard', className: 'bg-honey hover:bg-honey-dark' },
  { quality: 3, label: 'Good', className: 'bg-teal hover:bg-teal/90' },
  { quality: 4, label: 'Easy', className: 'bg-moss hover:bg-moss/90' },
];

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
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const currentCard = useMemo(() => dueWords[reviewIndex], [dueWords, reviewIndex]);

  async function handleGrade(quality: ReviewQuality) {
    if (!currentCard) return;
    const sched = nextSchedule(currentCard, quality);
    await updateWordSchedule(currentCard.word, sched);
    if (reviewIndex + 1 >= dueWords.length) { await refresh(); setTab('all'); }
    else { setReviewIndex(reviewIndex + 1); setRevealAnswer(false); }
  }

  const progress = dueWords.length > 0 ? ((reviewIndex) / dueWords.length) * 100 : 0;

  return (
    <main className="min-h-screen bg-cream px-4 py-8 text-ink">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="font-display text-2xl">Vocabulary</h1>
          <a href="#/" className="text-sm font-medium text-ink-light hover:text-honey transition-colors">{'←'} Home</a>
        </div>

        <div role="tablist" className="mb-6 inline-flex rounded-2xl border-2 border-sand bg-white p-1">
          <button role="tab" type="button" aria-selected={tab === 'all'} onClick={() => setTab('all')}
            className={`rounded-xl px-4 py-1.5 text-sm font-semibold transition-all duration-200
              ${tab === 'all' ? 'bg-honey text-white shadow-sm' : 'text-ink-light hover:bg-sand'}`}>
            All ({allWords.length})
          </button>
          <button role="tab" type="button" aria-selected={tab === 'review'} onClick={() => setTab('review')}
            className={`rounded-xl px-4 py-1.5 text-sm font-semibold transition-all duration-200
              ${tab === 'review' ? 'bg-honey text-white shadow-sm' : 'text-ink-light hover:bg-sand'}`}>
            Review ({dueWords.length})
          </button>
        </div>

        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <div key={i} className="skeleton h-16 w-full" />)}
          </div>
        )}

        {!loading && tab === 'all' && allWords.length === 0 && (
          <div className="card text-center py-10">
            <span className="text-4xl">{'\u{1F4DA}'}</span>
            <p className="mt-3 font-medium text-ink">No words yet</p>
            <p className="text-sm text-ink-light mt-1">Finish a chat session to collect vocabulary!</p>
          </div>
        )}

        {!loading && tab === 'all' && allWords.length > 0 && (
          <ul className="space-y-2">
            {allWords.map((w) => (
              <li key={w.word} className="card-hover flex items-center justify-between p-4">
                <div>
                  <p className="font-semibold text-ink">{w.word}</p>
                  {w.definition && <p className="text-xs text-ink-light mt-0.5">{w.definition}</p>}
                </div>
                <span className="text-xs font-medium text-ink-light/60">{formatDue(Date.now(), w.dueAt)}</span>
              </li>
            ))}
          </ul>
        )}

        {!loading && tab === 'review' && dueWords.length === 0 && (
          <div className="card text-center py-10">
            <span className="text-4xl">{'\u{2705}'}</span>
            <p className="mt-3 font-medium text-ink">All caught up!</p>
            <p className="text-sm text-ink-light mt-1">Come back tomorrow for review.</p>
          </div>
        )}

        {!loading && tab === 'review' && currentCard && (
          <div className="animate-pop-in">
            {/* Progress bar */}
            <div className="mb-4 flex items-center gap-3">
              <div className="flex-1 h-2 rounded-full bg-sand overflow-hidden">
                <div className="h-full rounded-full bg-honey transition-all duration-300"
                  style={{ width: `${progress}%` }} />
              </div>
              <span className="text-xs font-semibold text-ink-light">{reviewIndex + 1}/{dueWords.length}</span>
            </div>

            <div className="card text-center p-8">
              <p className="text-4xl font-display text-ink">{currentCard.word}</p>

              {!revealAnswer && (
                <button type="button" onClick={() => setRevealAnswer(true)}
                  className="btn-secondary mt-8 w-full justify-center text-base py-3">
                  Show answer
                </button>
              )}

              {revealAnswer && (
                <div className="mt-6 animate-slide-up">
                  {currentCard.definition && (
                    <p className="text-sm text-ink-light leading-relaxed">{currentCard.definition}</p>
                  )}
                  {currentCard.example && (
                    <p className="mt-3 text-sm italic text-ink-light/70 bg-sand/30 rounded-xl px-4 py-2">
                      "{currentCard.example}"
                    </p>
                  )}
                  <div className="mt-6 grid grid-cols-4 gap-2">
                    {GRADE_LABELS.map((g) => (
                      <button key={g.quality} type="button" onClick={() => handleGrade(g.quality)}
                        className={`rounded-xl px-2 py-2.5 text-xs font-semibold text-white transition-all duration-200 active:scale-95 ${g.className}`}>
                        {g.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-20 -right-20 w-80 h-80 rounded-full bg-honey-light/15 blur-3xl" />
        <div className="absolute bottom-10 -left-10 w-64 h-64 rounded-full bg-teal-light/20 blur-3xl" />
      </div>
    </main>
  );
}
