import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import MicButton from '../components/MicButton';

describe('MicButton', () => {
  let mockRecognition: any;

  beforeEach(() => {
    // Mock Web Speech API
    mockRecognition = {
      start: vi.fn(),
      stop: vi.fn(),
      lang: '',
      continuous: false,
      interimResults: false,
      onresult: null as any,
      onerror: null as any,
      onend: null as any,
    };
    (window as any).SpeechRecognition = vi.fn(() => mockRecognition);
    (window as any).webkitSpeechRecognition = undefined;
  });

  afterEach(() => {
    delete (window as any).SpeechRecognition;
  });

  it('renders mic button', () => {
    render(<MicButton onTranscript={() => {}} />);
    expect(screen.getByRole('button', { name: /start recording/i })).toBeInTheDocument();
  });

  it('shows disabled state when SpeechRecognition is not available', () => {
    delete (window as any).SpeechRecognition;
    render(<MicButton onTranscript={() => {}} />);
    expect(screen.getByRole('button', { name: /speech recognition not supported/i })).toBeDisabled();
  });
});
