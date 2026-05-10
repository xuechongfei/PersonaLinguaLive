import { describe, it, expect, beforeEach, vi } from 'vitest';
import { analyzeImage, ApiError } from './api';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
});

function jsonResponse(body: unknown, init: ResponseInit = { status: 200 }) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

describe('analyzeImage', () => {
  it('成功时返回 VisionAnalyzeResponse', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        request_id: 'req-1',
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

    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    const out = await analyzeImage(file);
    expect(out.objects).toHaveLength(1);
    expect(out.objects[0].label).toBe('cup');

    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe('/api/vision/analyze');
    expect((call[1] as RequestInit).method).toBe('POST');
  });

  it('UNSAFE_IMAGE 时抛 ApiError 携带 code', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          code: 'UNSAFE_IMAGE',
          message: '这张图不能用于学习。',
          details: { reject_reasons: ['face_detected'] },
        },
        { status: 422 },
      ),
    );
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    await expect(analyzeImage(file)).rejects.toMatchObject({
      code: 'UNSAFE_IMAGE',
      status: 422,
    });
  });

  it('429 时把 retry-after 透传到 ApiError', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          code: 'RATE_LIMITED',
          message: 'slow down',
          details: { retry_after_s: 7 },
        },
        { status: 429, headers: { 'Retry-After': '7' } },
      ),
    );
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    try {
      await analyzeImage(file);
      throw new Error('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).code).toBe('RATE_LIMITED');
      expect((e as ApiError).retryAfter).toBe(7);
    }
  });

  it('网络异常时抛 ApiError code=NETWORK', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    await expect(analyzeImage(file)).rejects.toMatchObject({ code: 'NETWORK' });
  });
});
