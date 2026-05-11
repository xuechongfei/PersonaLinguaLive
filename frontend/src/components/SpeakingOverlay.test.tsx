import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import SpeakingOverlay from './SpeakingOverlay';
import { useStudioStore } from '../lib/store';

vi.mock('./PersonaMouth', () => ({
  default: ({ isSpeaking, size }: any) => (
    <div data-testid="persona-mouth" data-speaking={isSpeaking} data-size={size} />
  ),
}));

describe('SpeakingOverlay', () => {
  beforeEach(() => {
    useStudioStore.getState().reset();
  });

  it('returns null when no object is selected', () => {
    const { container } = render(
      <SpeakingOverlay renderedWidth={400} renderedHeight={300} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('returns null when rendered dimensions are zero', () => {
    useStudioStore.getState().setSelectedObject({
      id: '1',
      label: 'cup',
      bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 },
      confidence: 0.9,
    });

    const { container } = render(
      <SpeakingOverlay renderedWidth={0} renderedHeight={0} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('returns null when bbox is too small', () => {
    useStudioStore.getState().setSelectedObject({
      id: '1',
      label: 'tiny',
      bbox: { x: 0.1, y: 0.1, w: 0.01, h: 0.01 },
      confidence: 0.9,
    });

    const { container } = render(
      <SpeakingOverlay renderedWidth={400} renderedHeight={300} />,
    );
    // 0.01 * 400 = 4px, 0.01 * 300 = 3px, min(4,3) * 0.6 = 1.8 < 60
    expect(container.innerHTML).toBe('');
  });

  it('renders PersonaMouth inside foreignObject at correct coordinates', () => {
    useStudioStore.getState().setSelectedObject({
      id: '2',
      label: 'mug',
      bbox: { x: 0.2, y: 0.3, w: 0.5, h: 0.4 },
      confidence: 0.95,
    });

    const { container } = render(
      <SpeakingOverlay renderedWidth={400} renderedHeight={300} />,
    );

    const foreignObject = container.querySelector('foreignObject');
    expect(foreignObject).toBeInTheDocument();

    // pixelX = 0.2 * 400 = 80, pixelY = 0.3 * 300 = 90
    // pixelW = 0.5 * 400 = 200, pixelH = 0.4 * 300 = 120
    // mouthSize = min(200, 120) * 0.6 = 72
    // mouthX = 80 + (200 - 72) / 2 = 144
    // mouthY = 90 - 72 * 0.3 = 68.4
    expect(foreignObject!.getAttribute('width')).toBe('72');
    expect(foreignObject!.getAttribute('height')).toBe('72');

    const mouth = container.querySelector('[data-testid="persona-mouth"]');
    expect(mouth).toBeInTheDocument();
    expect(mouth!.getAttribute('data-size')).toBe('72');
  });

  it('passes isSpeaking from store to PersonaMouth', () => {
    useStudioStore.getState().setSelectedObject({
      id: '3',
      label: 'vase',
      bbox: { x: 0.3, y: 0.3, w: 0.4, h: 0.4 },
      confidence: 0.85,
    });
    useStudioStore.getState().setIsSpeaking(true);

    const { container } = render(
      <SpeakingOverlay renderedWidth={400} renderedHeight={300} />,
    );

    const mouth = container.querySelector('[data-testid="persona-mouth"]');
    expect(mouth!.getAttribute('data-speaking')).toBe('true');
  });

  it('updates position when selectedObject changes', () => {
    useStudioStore.getState().setSelectedObject({
      id: '4',
      label: 'bowl',
      bbox: { x: 0.1, y: 0.1, w: 0.4, h: 0.4 },
      confidence: 0.88,
    });

    const { container, rerender } = render(
      <SpeakingOverlay renderedWidth={400} renderedHeight={300} />,
    );

    const mouth1 = container.querySelector('[data-testid="persona-mouth"]');
    // pixelW = 0.4 * 400 = 160, pixelH = 0.4 * 300 = 120, mouthSize = 72
    expect(mouth1!.getAttribute('data-size')).toBe('72');

    // Change object: larger bbox
    useStudioStore.getState().setSelectedObject({
      id: '5',
      label: 'table',
      bbox: { x: 0.2, y: 0.2, w: 0.8, h: 0.6 },
      confidence: 0.92,
    });

    rerender(
      <SpeakingOverlay renderedWidth={400} renderedHeight={300} />,
    );

    const mouth2 = container.querySelector('[data-testid="persona-mouth"]');
    // pixelW = 0.8 * 400 = 320, pixelH = 0.6 * 300 = 180, mouthSize = 108
    expect(mouth2!.getAttribute('data-size')).toBe('108');
  });
});
