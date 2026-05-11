import { useEffect, useState } from 'react';
import SummaryCard, { type SummaryData } from '../components/SummaryCard';
import {
  getAllConversationIds,
  getConversation,
  type ConversationData,
} from '../lib/storage';

type HistoryEntry = {
  id: string;
  personaName: string;
  createdAt: number;
  fluencyScore?: number;
  data: ConversationData;
};

function formatDate(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleString();
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
            id: c.sessionId,
            personaName: c.personaName,
            createdAt: c.createdAt,
            fluencyScore: c.summary?.fluencyScore,
            data: c,
          }))
          .sort((a, b) => b.createdAt - a.createdAt);
        if (!cancelled) setEntries(rows);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">History</h1>
          <a href="#/" className="text-sm text-indigo-600 hover:underline">
            ← Home
          </a>
        </div>

        {loading && <p className="text-sm text-slate-500">Loading…</p>}

        {!loading && entries.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
            No past sessions yet. Have a chat first!
          </p>
        )}

        <ul className="space-y-2">
          {entries.map((e) => (
            <li key={e.id}>
              <button
                type="button"
                onClick={() => setSelected(e)}
                className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 text-left hover:border-indigo-300"
              >
                <div>
                  <p className="font-medium text-slate-900">{e.personaName}</p>
                  <p className="text-xs text-slate-500">{formatDate(e.createdAt)}</p>
                </div>
                {typeof e.fluencyScore === 'number' && (
                  <span className="rounded-full bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">
                    Score {e.fluencyScore}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {selected && toSummaryData(selected.data) && (
        <SummaryCard
          summary={toSummaryData(selected.data)!}
          personaName={selected.personaName}
          onClose={() => setSelected(null)}
        />
      )}
      {selected && !toSummaryData(selected.data) && (
        <div
          role="dialog"
          aria-label="Session details"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="max-w-md rounded-2xl bg-white p-6 text-center shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-sm text-slate-600">
              No summary saved for this session ({selected.data.turns.length} turns).
            </p>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
