import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import StudioPage from './StudioPage';

// Mock API
vi.mock('../lib/api', () => ({
  analyzeImage: vi.fn(),
  generatePersona: vi.fn(),
  fetchSummary: vi.fn(),
  ApiError: class ApiError extends Error {
    code: string;
    status: number;
    constructor(opts: any) {
      super(opts.message);
      this.code = opts.code;
      this.status = opts.status;
    }
  },
}));

// Mock ChatClient
vi.mock('../lib/chat', () => ({
  ChatClient: vi.fn(() => ({
    on: vi.fn(),
    off: vi.fn(),
    connect: vi.fn(),
    sendMessage: vi.fn(),
    disconnect: vi.fn(),
    isConnected: true,
  })),
}));

// Mock child components that have side effects
vi.mock('../components/ChatPanel', () => ({
  default: ({ personaName, onEndChat }: any) => (
    <div role="dialog" aria-label="Chat panel">
      <span>{personaName}</span>
      <button onClick={onEndChat}>End Chat</button>
    </div>
  ),
}));

vi.mock('../components/SummaryCard', () => ({
  default: ({ personaName, onClose }: any) => (
    <div role="dialog" aria-label="Session summary">
      <span>{personaName}</span>
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

vi.mock('../lib/image/compress', () => ({
  compressIfNeeded: async (f: File) => f,
}));

import { analyzeImage, generatePersona, fetchSummary } from '../lib/api';

const mockAnalyzeResponse = {
  request_id: 'req',
  is_safe: true,
  reject_reasons: [],
  scene_summary: 'a cozy kitchen',
  objects: [
    {
      id: 'obj_1',
      label: 'teacup',
      bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 },
      confidence: 0.9,
    },
  ],
};

const mockPersonaResponse = {
  persona_id: 'p1',
  persona_name: 'Tilly the Teacup',
  description: 'A cheerful teacup',
  system_prompt: 'You are a cheerful teacup.',
  vocab_focus: ['teacup', 'tea'],
};

const mockSummaryResponse = {
  new_words: ['teacup'],
  grammar_points: ['Greetings'],
  fluency_score: 7,
  strengths: ['Vocabulary'],
  areas_to_improve: ['Grammar'],
};

describe('StudioPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    URL.createObjectURL = vi.fn(() => 'blob:fake') as typeof URL.createObjectURL;
    URL.revokeObjectURL = vi.fn();
    Element.prototype.scrollIntoView = vi.fn();

    (analyzeImage as any).mockResolvedValue(mockAnalyzeResponse);
    (generatePersona as any).mockResolvedValue(mockPersonaResponse);
    (fetchSummary as any).mockResolvedValue(mockSummaryResponse);
  });

  function setupImageUpload() {
    render(<StudioPage />);
    const input = screen.getByTestId('upload-input') as HTMLInputElement;
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [file] } });
    return file;
  }

  async function waitForImageLoad() {
    const img = await screen.findByRole('img');
    Object.defineProperty(img, 'naturalWidth', { value: 800, configurable: true });
    Object.defineProperty(img, 'naturalHeight', { value: 600, configurable: true });
    Object.defineProperty(img, 'clientWidth', { value: 400, configurable: true });
    Object.defineProperty(img, 'clientHeight', { value: 300, configurable: true });
    img.dispatchEvent(new Event('load'));
    return img;
  }

  it('uploads image and renders hotspot overlay', async () => {
    setupImageUpload();
    await waitForImageLoad();

    const hotspot = await screen.findByRole('button', { name: /teacup/i });
    expect(hotspot).toBeInTheDocument();
  });

  it('clicking hotspot generates persona and opens chat', async () => {
    setupImageUpload();
    await waitForImageLoad();

    const hotspot = await screen.findByRole('button', { name: /teacup/i });
    fireEvent.click(hotspot);

    // Should show persona loading indicator
    expect(screen.getByText(/Creating persona/)).toBeInTheDocument();

    // After persona generated, chat panel appears
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /chat/i })).toBeInTheDocument();
    });

    // Chat panel shows persona name
    expect(screen.getByText('Tilly the Teacup')).toBeInTheDocument();
  });

  it('clicking End Chat triggers summary', async () => {
    setupImageUpload();
    await waitForImageLoad();

    // Open chat
    const hotspot = await screen.findByRole('button', { name: /teacup/i });
    fireEvent.click(hotspot);

    // Wait for chat
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /chat/i })).toBeInTheDocument();
    });

    // End chat
    fireEvent.click(screen.getByText('End Chat'));

    // Summary should appear
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /summary/i })).toBeInTheDocument();
    });

    expect(fetchSummary).toHaveBeenCalled();
  });

  it('shows error when persona generation fails', async () => {
    (generatePersona as any).mockRejectedValue(new Error('API error'));

    setupImageUpload();
    await waitForImageLoad();

    const hotspot = await screen.findByRole('button', { name: /teacup/i });
    fireEvent.click(hotspot);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('shows error on failed analysis', async () => {
    (analyzeImage as any).mockRejectedValue(new Error('Network error'));

    setupImageUpload();
    await waitForImageLoad(); // Image loads even though API fails

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
});
