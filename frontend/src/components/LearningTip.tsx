import { useState } from 'react';

interface Props { learning: string; followup: string; }

export default function LearningTip({ learning, followup }: Props) {
  const [open, setOpen] = useState(false);
  const hasContent = learning.length > 0 || followup.length > 0;

  if (!hasContent) return null;

  return (
    <div className="rounded-2xl bg-teal-light/40 border border-teal/10 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-3.5 py-2.5 text-left hover:bg-teal-light/30 transition-colors"
      >
        <span className="text-xs font-semibold text-teal flex items-center gap-1.5">
          <span>{'\u{1F4A1}'}</span> Learning Tip
        </span>
        <span className={`text-teal text-xs transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>
          {'\u{25BC}'}
        </span>
      </button>
      {open && (
        <div className="px-3.5 pb-3 space-y-2 animate-slide-up">
          {learning && (
            <div>
              <span className="text-[10px] font-semibold text-teal/70 uppercase tracking-wider">Notes</span>
              <p className="mt-0.5 text-xs text-ink-light leading-relaxed">{learning}</p>
            </div>
          )}
          {followup && (
            <div>
              <span className="text-[10px] font-semibold text-teal/70 uppercase tracking-wider">Try Saying</span>
              <p className="mt-0.5 text-xs font-medium text-honey-dark italic">"{followup}"</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
