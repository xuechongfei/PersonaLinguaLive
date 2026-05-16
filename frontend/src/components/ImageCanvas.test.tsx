import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ImageCanvas from './ImageCanvas';

describe('ImageCanvas', () => {
  it('为传入的 file 渲染 <img> 并设置 alt', () => {
    const created: string[] = [];
    const origCreate = URL.createObjectURL;
    URL.createObjectURL = vi.fn((blob: Blob) => {
      const url = `blob:fake-${created.length}`;
      created.push(url);
      void blob;
      return url;
    }) as typeof URL.createObjectURL;
    URL.revokeObjectURL = vi.fn();

    const file = new File([new Uint8Array(10)], 'pic.jpg', { type: 'image/jpeg' });
    render(<ImageCanvas file={file} alt="用户上传的图片" />);
    const img = screen.getByRole('img') as HTMLImageElement;
    expect(img.src.startsWith('blob:')).toBe(true);
    expect(img.alt).toBe('用户上传的图片');

    URL.createObjectURL = origCreate;
  });

  it('onLoad 时通过 onReady 回调汇报渲染尺寸', async () => {
    const onReady = vi.fn();
    URL.createObjectURL = vi.fn(() => 'blob:fake') as typeof URL.createObjectURL;
    URL.revokeObjectURL = vi.fn();

    // Mock rAF to call callback synchronously
    const origRaf = window.requestAnimationFrame;
    window.requestAnimationFrame = vi.fn((cb: FrameRequestCallback) => {
      cb(0);
      return 0;
    });

    const file = new File([new Uint8Array(10)], 'pic.jpg', { type: 'image/jpeg' });
    render(<ImageCanvas file={file} alt="x" onReady={onReady} />);
    const img = screen.getByRole('img') as HTMLImageElement;

    // Mock getBoundingClientRect
    img.getBoundingClientRect = vi.fn(() => ({
      width: 600, height: 400, x: 0, y: 0, top: 0, left: 0,
      right: 600, bottom: 400, toJSON: () => {},
    }));

    Object.defineProperty(img, 'naturalWidth', { value: 1200, configurable: true });
    Object.defineProperty(img, 'naturalHeight', { value: 800, configurable: true });

    img.dispatchEvent(new Event('load'));
    expect(onReady).toHaveBeenCalledWith({
      naturalWidth: 1200,
      naturalHeight: 800,
      renderedWidth: 600,
      renderedHeight: 400,
    });

    window.requestAnimationFrame = origRaf;
  });
});
