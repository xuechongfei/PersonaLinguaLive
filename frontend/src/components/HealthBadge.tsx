import { useEffect, useState } from 'react';
import { fetchHealth, type HealthPayload } from '../lib/api';

type State =
  | { kind: 'checking' }
  | { kind: 'ok'; data: HealthPayload }
  | { kind: 'error'; message: string };

export default function HealthBadge() {
  const [state, setState] = useState<State>({ kind: 'checking' });

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((data) => { if (!cancelled) setState({ kind: 'ok', data }); })
      .catch((e: unknown) => {
        if (!cancelled) setState({ kind: 'error', message: e instanceof Error ? e.message : 'Unknown error' });
      });
    return () => { cancelled = true; };
  }, []);

  const base = 'inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-full';

  if (state.kind === 'checking') {
    return <span className={`${base} bg-sand text-ink-light`}><span className="w-1.5 h-1.5 rounded-full bg-honey animate-pulse-soft" />Checking...</span>;
  }
  if (state.kind === 'error') {
    return <span className={`${base} bg-rose-light text-rose`} title={state.message}><span className="w-1.5 h-1.5 rounded-full bg-rose" />Backend offline</span>;
  }
  return (
    <span className={`${base} bg-moss-light/50 text-moss`}>
      <span className="w-1.5 h-1.5 rounded-full bg-moss" />
      {state.data.app} v{state.data.version} · {state.data.environment}
    </span>
  );
}
