export type UserLevel = 'beginner' | 'intermediate' | 'advanced';

interface Props {
  value: UserLevel;
  onChange: (level: UserLevel) => void;
}

const LEVELS: { value: UserLevel; label: string }[] = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
];

export default function LevelSelector({ value, onChange }: Props) {
  return (
    <div
      role="radiogroup"
      aria-label="English level"
      className="inline-flex overflow-hidden rounded-lg border border-slate-300 bg-white"
    >
      {LEVELS.map(({ value: val, label }) => {
        const isActive = value === val;
        return (
          <button
            key={val}
            role="radio"
            type="button"
            aria-checked={isActive}
            onClick={() => onChange(val)}
            className={
              isActive
                ? 'bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white'
                : 'bg-white px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50'
            }
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
