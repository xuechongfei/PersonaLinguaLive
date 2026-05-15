import HealthBadge from '../components/HealthBadge';

interface Props {
  onStart: () => void;
}

const FEATURES = [
  { icon: '\u{1F4F7}', title: 'Upload', desc: 'Snap a photo of your surroundings' },
  { icon: '\u{1F91D}', title: 'Click', desc: 'Tap any object to bring it to life' },
  { icon: '\u{1F5E3}', title: 'Speak', desc: 'Chat naturally and learn English' },
];

export default function HomePage({ onStart }: Props) {
  return (
    <main className="min-h-screen bg-cream flex flex-col items-center justify-center px-4 py-12">
      {/* Hero */}
      <div className="text-center max-w-2xl animate-slide-up">
        {/* Floating emoji scene */}
        <div className="mb-8 flex items-center justify-center gap-4 text-5xl select-none">
          <span className="animate-float" style={{ animationDelay: '0s' }}>{'\u{1F4F7}'}</span>
          <span className="text-3xl text-sand">→</span>
          <span className="animate-float" style={{ animationDelay: '0.3s' }}>{'\u{2728}'}</span>
          <span className="text-3xl text-sand">→</span>
          <span className="animate-float" style={{ animationDelay: '0.6s' }}>{'\u{1F5E3}'}</span>
        </div>

        <h1 className="font-display text-5xl sm:text-6xl text-ink tracking-tight leading-tight">
          Your photos come
          <br />
          <span className="text-honey">alive in English</span>
        </h1>

        <p className="mt-5 text-lg text-ink-light leading-relaxed max-w-lg mx-auto">
          Upload a photo, tap any object, and start speaking. Every lamp, coffee cup, and
          chair becomes your personal English tutor.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
          <button type="button" onClick={onStart} className="btn-primary text-base px-8 py-3.5">
            <span>{'\u{2728}'}</span>
            Start Learning Free
          </button>
          <button type="button" onClick={onStart} className="btn-secondary text-base px-8 py-3.5">
            Browse Built-in Scenes
          </button>
        </div>
      </div>

      {/* Feature cards */}
      <div className="mt-20 grid grid-cols-1 sm:grid-cols-3 gap-5 max-w-3xl w-full">
        {FEATURES.map((f, i) => (
          <div
            key={f.title}
            className="card-hover text-center animate-slide-up"
            style={{ animationDelay: `${0.2 + i * 0.1}s` }}
          >
            <span className="text-3xl">{f.icon}</span>
            <h3 className="mt-3 font-semibold text-ink">{f.title}</h3>
            <p className="mt-1 text-sm text-ink-light">{f.desc}</p>
          </div>
        ))}
      </div>

      {/* Footer nav */}
      <div className="mt-12 flex gap-6 text-sm font-medium">
        <a href="#/history" className="text-ink-light hover:text-honey transition-colors">
          History
        </a>
        <a href="#/vocab" className="text-ink-light hover:text-honey transition-colors">
          Vocabulary
        </a>
      </div>

      <div className="mt-6">
        <HealthBadge />
      </div>

      {/* Subtle background decoration */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-honey-light/20 blur-3xl" />
        <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full bg-teal-light/30 blur-3xl" />
      </div>
    </main>
  );
}
