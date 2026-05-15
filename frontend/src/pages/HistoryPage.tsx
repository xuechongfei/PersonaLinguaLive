import { useEffect, useState } from 'react';
import SummaryCard, { type SummaryData } from '../components/SummaryCard';
import { getAllConversationIds, getConversation, type ConversationData } from '../lib/storage';

type HistoryEntry = {
  id: string;
  personaName: string;
  createdAt: number;
  fluencyScore?: number;
  data: ConversationData;
};

function formatDate(ms: number): string {
  return new Date(ms).toLocaleString();
}

function toSummaryData(c: ConversationData): SummaryData | null {
  if (!c.summary) return null;
  return {
    newWords: c.summary.newWords,
    grammarPoints: c.summary.grammarPoints,
    fluencyScore: c.summary.fluencyScore,
    strengths: c.summary.strengths,
    areasToImprove: c.summary.areasToImprove,
  };
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<HistoryEntry | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const ids = await getAllConversationIds();
        const records = await Promise.all(ids.map((id) => getConversation(id)));
        const rows: HistoryEntry[] = records
          .filter((c): c is ConversationData => Boolean(c))
          .map((c) => ({
            id: c.sessionId, personaName: c.personaName,
            createdAt: c.createdAt, fluencyScore: c.summary?.fluencyScore, data: c,
          }))
          .sort((a, b) => b.createdAt - a.createdAt);
        if (!cancelled) setEntries(rows);
      } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <main className="min-h-screen bg-cream px-4 py-8 text-ink">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="font-display text-2xl">History</h1>
          <a href="#/" className="text-sm font-medium text-ink-light hover:text-honey transition-colors">{'←'} Home</a>
        </div>

        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <div key={i} className="skeleton h-16 w-full" />)}
          </div>
        )}

        {!loading && entries.length === 0 && (
          <div className="card text-center py-10">
            <span className="text-4xl">{'\u{1F4AC}'}</span>
            <p className="mt-3 font-medium text-ink">No past sessions</p>
            <p className="text-sm text-ink-light mt-1">Have a chat first to build your history!</p>
          </div>
        )}

        <ul className="space-y-2">
          {entries.map((e) => (
            <li key={e.id}>
              <button type="button" onClick={() => setSelected(e)}
                className="card-hover flex w-full items-center justify-between p-4 text-left">
                <div>
                  <p className="font-semibold text-ink">{e.personaName}</p>
                  <p className="text-xs text-ink-light mt-0.5">{formatDate(e.createdAt)}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-ink-light/50">{e.data.turns.length} turns</span>
                  {typeof e.fluencyScore === 'number' && (
                    <span className="rounded-full bg-honey-light px-2.5 py-1 text-xs font-semibold text-honey-dark">
                      {e.fluencyScore}/10
                    </span>
                  )}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {selected && toSummaryData(selected.data) && (
        <SummaryCard summary={toSummaryData(selected.data)!} personaName={selected.personaName}
          onClose={() => setSelected(null)} />
      )}
      {selected && !toSummaryData(selected.data) && (
        <div role="dialog" aria-label="Session details"
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/20 backdrop-blur-sm p-4"
          onClick={() => setSelected(null)}>
          <div className="card max-w-md text-center" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm text-ink-light">
              No summary saved ({selected.data.turns.length} turns).
            </p>
            <button type="button" onClick={() => setSelected(null)} className="btn-primary mt-4">
              Close
            </button>
          </div>
        </div>
      )}

      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-20 -right-20 w-80 h-80 rounded-full bg-honey-light/15 blur-3xl" />
        <div className="absolute bottom-10 -left-10 w-64 h-64 rounded-full bg-teal-light/20 blur-3xl" />
      </div>
    </main>
  );
}
