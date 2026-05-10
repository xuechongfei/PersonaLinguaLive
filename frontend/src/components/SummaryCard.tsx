export interface SummaryData {
  newWords: string[];
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
}

function scoreColor(score: number): string {
  if (score <= 3) return 'bg-red-100 text-red-700 border-red-300';
  if (score <= 6) return 'bg-amber-100 text-amber-700 border-amber-300';
  return 'bg-green-100 text-green-700 border-green-300';
}

export default function SummaryCard({ summary, personaName, onClose, onPracticeAgain }: Props) {
  const hasContent =
    summary.newWords.length > 0 ||
    summary.grammarPoints.length > 0 ||
    summary.strengths.length > 0 ||
    summary.areasToImprove.length > 0;

  return (
    <div
      role="dialog"
      aria-label="Session summary"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
    >
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Session Summary</h2>
            <p className="text-sm text-slate-500">with {personaName}</p>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close summary"
              className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100"
            >
              ×
            </button>
          )}
        </div>

        {/* Fluency Score */}
        <div className="mt-6 flex flex-col items-center">
          <div
            className={`flex h-20 w-20 items-center justify-center rounded-full border-4 text-3xl font-bold ${scoreColor(summary.fluencyScore)}`}
          >
            {summary.fluencyScore}
          </div>
          <p className="mt-2 text-sm font-medium text-slate-600">Fluency Score</p>
        </div>

        {hasContent && (
          <div className="mt-6 space-y-4">
            {/* New Words */}
            {summary.newWords.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-700">New Words</h3>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {summary.newWords.map((word) => (
                    <span
                      key={word}
                      className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700"
                    >
                      {word}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Grammar Points */}
            {summary.grammarPoints.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-700">Grammar Points</h3>
                <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-slate-600">
                  {summary.grammarPoints.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Strengths */}
            {summary.strengths.length > 0 && (
              <div className="rounded-lg bg-green-50 p-3">
                <h3 className="text-sm font-semibold text-green-800">Strengths</h3>
                <ul className="mt-1 space-y-0.5 text-sm text-green-700">
                  {summary.strengths.map((s) => (
                    <li key={s} className="flex items-start gap-1.5">
                      <span>+</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Areas to Improve */}
            {summary.areasToImprove.length > 0 && (
              <div className="rounded-lg bg-amber-50 p-3">
                <h3 className="text-sm font-semibold text-amber-800">Areas to Improve</h3>
                <ul className="mt-1 space-y-0.5 text-sm text-amber-700">
                  {summary.areasToImprove.map((a) => (
                    <li key={a} className="flex items-start gap-1.5">
                      <span>→</span> {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {!hasContent && (
          <p className="mt-6 text-center text-sm text-slate-400">
            No learning data available for this session.
          </p>
        )}

        {/* Footer */}
        <div className="mt-6 flex justify-end gap-3">
          {onPracticeAgain && (
            <button
              type="button"
              onClick={onPracticeAgain}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Practice Again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
