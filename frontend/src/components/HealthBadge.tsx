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
      .then((data) => {
        if (!cancelled) setState({ kind: 'ok', data });
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'Unknown error';
          setState({ kind: 'error', message: msg });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === 'checking') {
    return (
      <span className="inline-flex items-center rounded-full bg-slate-200 px-3 py-1 text-xs text-slate-700">
        Checking backend…
      </span>
    );
  }
  if (state.kind === 'error') {
    return (
      <span
        className="inline-flex items-center rounded-full bg-rose-100 px-3 py-1 text-xs text-rose-700"
        title={state.message}
      >
        Backend offline / unavailable
      </span>
    );
  }
  const { app, version, environment } = state.data;
  return (
    <span className="inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-xs text-emerald-800">
      {app} v{version} · {environment}
    </span>
  );
}
