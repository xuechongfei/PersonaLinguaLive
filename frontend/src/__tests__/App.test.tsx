import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => ({ status: 'ok', app: 'PersonaLinguaLive', version: '0.1.0', environment: 'development' }),
  } as unknown as Response);
});

afterEach(() => { globalThis.fetch = originalFetch; });

describe('App', () => {
  it('renders the product name', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/Your photos come/)).toBeInTheDocument();
  });

  it('renders the feature cards', () => {
    render(<App />);
    expect(screen.getByText('Upload')).toBeInTheDocument();
    expect(screen.getByText('Click')).toBeInTheDocument();
    expect(screen.getByText('Speak')).toBeInTheDocument();
  });
});
