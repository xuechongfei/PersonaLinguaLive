import { useEffect } from 'react';
import type { VocabEntry } from '../lib/api';
import { saveWord } from '../lib/storage';

export interface SummaryData {
  newWords: VocabEntry[];
  grammarPoints: string[];
  fluencyScore: number;
  strengths: string[];
  areasToImprove: string[];
}

interface Props {
  summary: SummaryData;
  personaName: string;
  onClose?: () => void;
  onPracticeAgain?: () => void;
  sessionId?: string;
  autoSaveWords?: boolean;
}

function scoreLabel(score: number): { text: string; ring: string; bg: string } {
  if (score <= 3) return { text: 'Keep Going', ring: 'stroke-rose', bg: 'bg-rose-light text-rose' };
  if (score <= 6) return { text: 'Getting There', ring: 'stroke-honey', bg: 'bg-honey-light text-honey-dark' };
  return { text: 'Great Job', ring: 'stroke-moss', bg: 'bg-moss-light text-moss' };
}

export default function SummaryCard({
  summary, personaName, onClose, onPracticeAgain, sessionId, autoSaveWords = true,
}: Props) {
  useEffect(() => {
    if (!autoSaveWords) return;
    const now = Date.now();
    summary.newWords.forEach((entry) => {
      saveWord({
        word: entry.word, definition: entry.definition, example: entry.example,
        sessionId: sessionId ?? '', addedAt: now, dueAt: now,
        ease: 2.5, intervalDays: 0, reps: 0,
      }).catch(() => {});
    });
  }, [summary.newWords, sessionId, autoSaveWords]);

  const hasContent = summary.newWords.length > 0 || summary.grammarPoints.length > 0
    || summary.strengths.length > 0 || summary.areasToImprove.length > 0;

  const sl = scoreLabel(summary.fluencyScore);
  const circumference = 2 * Math.PI * 42;
  const progress = (summary.fluencyScore / 10) * circumference;

  return (
    <div
      role="dialog" aria-label="Session summary"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/20 backdrop-blur-sm p-4 animate-pop-in"
    >
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-3xl bg-white shadow-card p-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="font-display text-xl text-ink">Session Summary</h2>
            <p className="text-sm text-ink-light">with {personaName}</p>
          </div>
          {onClose && (
            <button type="button" onClick={onClose} aria-label="Close"
              className="w-8 h-8 flex items-center justify-center rounded-full text-ink-light hover:bg-sand hover:text-ink transition-colors">
              {'×'}
            </button>
          )}
        </div>

        {/* Fluency ring */}
        <div className="mt-6 flex flex-col items-center">
          <div className="relative w-28 h-28">
            <svg viewBox="0 0 100 100" className="w-28 h-28 -rotate-90">
              <circle cx="50" cy="50" r="42" fill="none" stroke="#F5E6D3" strokeWidth="8" />
              <circle cx="50" cy="50" r="42" fill="none"
                className={sl.ring}
                strokeWidth="8" strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={circumference - progress}
                style={{ transition: 'stroke-dashoffset 1s ease-out' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-display text-2xl text-ink">{summary.fluencyScore}</span>
              <span className="text-[10px] font-semibold text-ink-light">/10</span>
            </div>
          </div>
          <span className={`mt-2 px-3 py-0.5 rounded-full text-xs font-semibold ${sl.bg}`}>{sl.text}</span>
        </div>

        {hasContent && (
          <div className="mt-6 space-y-4">
            {summary.newWords.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-ink-light uppercase tracking-wider">New Words</h3>
                <ul className="mt-2 space-y-1.5">
                  {summary.newWords.map((entry) => (
                    <li key={entry.word} className="rounded-xl bg-sand/30 px-3.5 py-2.5">
                      <p className="font-semibold text-sm text-ink">{entry.word}</p>
                      {entry.definition && <p className="mt-0.5 text-xs text-ink-light">{entry.definition}</p>}
                      {entry.example && <p className="mt-0.5 text-xs italic text-ink-light/70">"{entry.example}"</p>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {summary.grammarPoints.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-ink-light uppercase tracking-wider">Grammar</h3>
                <ul className="mt-2 list-disc list-inside space-y-0.5 text-sm text-ink-light">
                  {summary.grammarPoints.map((p) => <li key={p}>{p}</li>)}
                </ul>
              </div>
            )}
            {summary.strengths.length > 0 && (
              <div className="rounded-xl bg-moss-light/50 px-4 py-3">
                <h3 className="text-xs font-semibold text-moss uppercase tracking-wider">Strengths</h3>
                <ul className="mt-1.5 space-y-0.5 text-sm text-moss/90">
                  {summary.strengths.map((s) => <li key={s} className="flex gap-1.5"><span>+</span>{s}</li>)}
                </ul>
              </div>
            )}
            {summary.areasToImprove.length > 0 && (
              <div className="rounded-xl bg-honey-light/30 px-4 py-3">
                <h3 className="text-xs font-semibold text-honey-dark uppercase tracking-wider">To Improve</h3>
                <ul className="mt-1.5 space-y-0.5 text-sm text-honey-dark/80">
                  {summary.areasToImprove.map((a) => <li key={a} className="flex gap-1.5"><span>{'→'}</span>{a}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        {!hasContent && (
          <p className="mt-6 text-center text-sm text-ink-light">No learning data for this session yet.</p>
        )}

        {onPracticeAgain && (
          <button type="button" onClick={onPracticeAgain} className="btn-primary w-full mt-6 justify-center">
            Practice Again
          </button>
        )}
      </div>
    </div>
  );
}
