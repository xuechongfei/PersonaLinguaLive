import { useState } from 'react';

interface Props {
  learning: string;
  followup: string;
}

export default function LearningTip({ learning, followup }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasContent = learning.length > 0 || followup.length > 0;

  if (!hasContent) return null;

  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        aria-label="Toggle learning tip"
        className="flex w-full items-center justify-between text-left font-medium text-sky-800"
      >
        <span>Learning Tip</span>
        <span className="text-sky-500 transition-transform duration-200 data-[expanded=true]:rotate-180">
          {expanded ? '▲' : '▼'}
        </span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-2 border-t border-sky-200 pt-3">
          {learning && (
            <div className="text-slate-700">
              <span className="font-semibold text-sky-700">学习要点:</span>
              <p className="mt-1 whitespace-pre-wrap">{learning}</p>
            </div>
          )}
          {followup && (
            <div className="text-slate-700">
              <span className="font-semibold text-sky-700">继续练习:</span>
              <p className="mt-1 whitespace-pre-wrap italic">{followup}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
