import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PersonaPlaceholderPanel from './PersonaPlaceholderPanel';
import type { DetectedObject } from '../lib/api';

const obj: DetectedObject = {
  id: 'obj_1',
  label: 'cup',
  bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 },
  confidence: 0.9,
};

describe('PersonaPlaceholderPanel', () => {
  it('展示标签并提示后续阶段会接入对话', () => {
    render(<PersonaPlaceholderPanel object={obj} onClose={() => {}} />);
    expect(screen.getByText(/cup/)).toBeInTheDocument();
    expect(screen.getByText(/Phase 3/)).toBeInTheDocument();
  });

  it('点击关闭按钮回调 onClose', () => {
    const onClose = vi.fn();
    render(<PersonaPlaceholderPanel object={obj} onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /关闭|close/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
