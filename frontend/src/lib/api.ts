export interface HealthPayload {
  status: 'ok';
  app: string;
  version: string;
  environment: 'development' | 'production' | 'test';
}

const BASE_URL = import.meta.env.VITE_API_BASE ?? '';

export async function fetchHealth(): Promise<HealthPayload> {
  const resp = await fetch(`${BASE_URL}/healthz`);
  if (!resp.ok) {
    throw new Error(`Health check failed with status ${resp.status}`);
  }
  return (await resp.json()) as HealthPayload;
}
