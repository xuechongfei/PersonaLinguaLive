export type UserLevel = 'beginner' | 'intermediate' | 'advanced';

interface Props { value: UserLevel; onChange: (level: UserLevel) => void; }

const LEVELS: { value: UserLevel; label: string; icon: string }[] = [
  { value: 'beginner', label: 'Beginner', icon: '\u{1F331}' },
  { value: 'intermediate', label: 'Intermediate', icon: '\u{1F33F}' },
  { value: 'advanced', label: 'Advanced', icon: '\u{1F333}' },
];

export default function LevelSelector({ value, onChange }: Props) {
  return (
    <div role="radiogroup" aria-label="English level" className="inline-flex rounded-2xl border-2 border-sand bg-white p-1 gap-0.5">
      {LEVELS.map(({ value: val, label, icon }) => {
        const isActive = value === val;
        return (
          <button
            key={val}
            role="radio"
            type="button"
            aria-checked={isActive}
            onClick={() => onChange(val)}
            className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-sm font-semibold transition-all duration-200
              ${isActive
                ? 'bg-honey text-white shadow-sm'
                : 'text-ink-light hover:bg-sand hover:text-ink'}`}
          >
            <span>{icon}</span>
            {label}
          </button>
        );
      })}
    </div>
  );
}
