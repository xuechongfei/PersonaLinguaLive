import type { DetectedObject } from '../lib/api';

interface Props {
  object: DetectedObject;
  onClose: () => void;
}

export default function PersonaPlaceholderPanel({ object, onClose }: Props) {
  return (
    <aside
      role="dialog"
      aria-label={`${object.label} 的占位面板`}
      className="fixed right-4 top-4 z-30 w-80 rounded-2xl border border-slate-200 bg-white p-5 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500">已识别</p>
          <h2 className="text-lg font-semibold text-slate-900">{object.label}</h2>
        </div>
        <button
          type="button"
          aria-label="关闭"
          onClick={onClose}
          className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100"
        >
          ×
        </button>
      </header>
      <p className="mt-3 text-sm text-slate-600">
        Phase 3 会把它变成可对话的 Persona。当下你可以继续点击其他热点感受识别效果。
      </p>
      <p className="mt-2 text-xs text-slate-400">
        confidence ≈ {object.confidence.toFixed(2)} · id {object.id}
      </p>
    </aside>
  );
}
