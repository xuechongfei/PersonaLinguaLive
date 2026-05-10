import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchHealth } from '../lib/api';

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe('fetchHealth', () => {
  it('returns parsed payload on 200', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'ok',
        app: 'PersonaLinguaLive',
        version: '0.1.0',
        environment: 'development',
      }),
    } as unknown as Response);

    const result = await fetchHealth();
    expect(result.status).toBe('ok');
    expect(result.version).toBe('0.1.0');
  });

  it('throws on non-2xx', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({}),
    } as unknown as Response);

    await expect(fetchHealth()).rejects.toThrow(/503/);
  });
});
