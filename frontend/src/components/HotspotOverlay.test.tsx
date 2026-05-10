import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HotspotOverlay from './HotspotOverlay';
import type { DetectedObject } from '../lib/api';

const objects: DetectedObject[] = [
  { id: 'obj_1', label: 'cup', bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 }, confidence: 0.9 },
  { id: 'obj_2', label: 'lamp', bbox: { x: 0.5, y: 0.5, w: 0.1, h: 0.1 }, confidence: 0.8 },
];

describe('HotspotOverlay', () => {
  it('渲染与对象数量匹配的 hotspot 元素', () => {
    render(
      <HotspotOverlay
        renderedWidth={400}
        renderedHeight={300}
        objects={objects}
        onSelect={() => {}}
      />,
    );
    expect(screen.getAllByRole('button', { name: /cup|lamp/ })).toHaveLength(2);
  });

  it('点击 hotspot 触发 onSelect 并传入对应对象', () => {
    const onSelect = vi.fn();
    render(
      <HotspotOverlay
        renderedWidth={400}
        renderedHeight={300}
        objects={objects}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /cup/ }));
    expect(onSelect).toHaveBeenCalledWith(objects[0]);
  });

  it('SVG viewBox 与 renderedWidth/Height 一致', () => {
    const { container } = render(
      <HotspotOverlay
        renderedWidth={500}
        renderedHeight={250}
        objects={objects}
        onSelect={() => {}}
      />,
    );
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('viewBox')).toBe('0 0 500 250');
  });
});
