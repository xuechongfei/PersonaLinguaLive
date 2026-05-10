import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import StudioPage from './StudioPage';

vi.mock('../lib/image/compress', () => ({
  compressIfNeeded: async (f: File) => f,
}));

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
  URL.createObjectURL = vi.fn(() => 'blob:fake') as typeof URL.createObjectURL;
  URL.revokeObjectURL = vi.fn();
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('StudioPage', () => {
  it('上传 → 调用 analyze → 渲染热点 → 点击弹面板', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        request_id: 'req',
        is_safe: true,
        reject_reasons: [],
        scene_summary: 'kitchen',
        objects: [
          {
            id: 'obj_1',
            label: 'cup',
            bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 },
            confidence: 0.9,
          },
        ],
      }),
    );

    render(<StudioPage />);
    const input = screen.getByTestId('upload-input') as HTMLInputElement;
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [file] } });

    const img = await screen.findByRole('img');
    Object.defineProperty(img, 'naturalWidth', { value: 800, configurable: true });
    Object.defineProperty(img, 'naturalHeight', { value: 600, configurable: true });
    Object.defineProperty(img, 'clientWidth', { value: 400, configurable: true });
    Object.defineProperty(img, 'clientHeight', { value: 300, configurable: true });
    img.dispatchEvent(new Event('load'));

    const hotspot = await screen.findByRole('button', { name: /cup/ });
    fireEvent.click(hotspot);
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());
  });

  it('analyze 返回 UNSAFE 时显示错误而不是热点', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        { code: 'UNSAFE_IMAGE', message: '这张图不能用于学习。', details: { reject_reasons: ['face_detected'] } },
        422,
      ),
    );

    render(<StudioPage />);
    const input = screen.getByTestId('upload-input') as HTMLInputElement;
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByRole('alert')).toHaveTextContent(/不能用于学习/);
  });
});
