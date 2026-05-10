import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HealthBadge from '../components/HealthBadge';

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe('HealthBadge', () => {
  it('shows checking → ok when API responds 200', async () => {
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

    render(<HealthBadge />);

    expect(screen.getByText(/checking/i)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/v0\.1\.0/)).toBeInTheDocument()
    );
    expect(screen.getByText(/development/)).toBeInTheDocument();
  });

  it('shows error state when API fails', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({}),
    } as unknown as Response);

    render(<HealthBadge />);
    await waitFor(() =>
      expect(screen.getByText(/offline|unavailable/i)).toBeInTheDocument()
    );
  });
});
