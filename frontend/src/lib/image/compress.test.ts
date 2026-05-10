import { describe, it, expect, vi, beforeEach } from 'vitest';
import { compressIfNeeded } from './compress';

class FakeImage {
  width = 0;
  height = 0;
  src = '';
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor() {
    (globalThis as unknown as { __lastImage?: FakeImage }).__lastImage = this;
    queueMicrotask(() => {
      this.width = 4000;
      this.height = 3000;
      this.onload?.();
    });
  }
}

beforeEach(() => {
  (globalThis as unknown as { Image: typeof FakeImage }).Image = FakeImage;
});

function fakeCanvasReturning(blob: Blob | null) {
  const ctx = { drawImage: vi.fn() };
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => ctx,
    toBlob: (cb: (b: Blob | null) => void) => cb(blob),
  };
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
    if (tag === 'canvas') return canvas as unknown as HTMLCanvasElement;
    return document.createElementNS('http://www.w3.org/1999/xhtml', tag) as HTMLElement;
  });
  return canvas;
}

function makeFile(name: string, type: string, size: number): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe('compressIfNeeded', () => {
  it('小于阈值且最长边足够小,直接返回原文件', async () => {
    const original = makeFile('a.jpg', 'image/jpeg', 100 * 1024);
    const out = await compressIfNeeded(original, { maxEdge: 1600, sizeThresholdBytes: 1_500_000 });
    expect(out).toBe(original);
  });

  it('超过 sizeThreshold 时尝试压缩,产物为 image/jpeg', async () => {
    const original = makeFile('big.jpg', 'image/jpeg', 5 * 1024 * 1024);
    const compressedBlob = new Blob([new Uint8Array(800 * 1024)], { type: 'image/jpeg' });
    fakeCanvasReturning(compressedBlob);

    const out = await compressIfNeeded(original, {
      maxEdge: 1600,
      sizeThresholdBytes: 1_500_000,
    });

    expect(out.type).toBe('image/jpeg');
    expect(out.size).toBeLessThan(original.size);
  });
});
