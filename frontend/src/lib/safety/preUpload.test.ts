import { describe, it, expect } from 'vitest';
import { preCheckFile, MAX_UPLOAD_BYTES, ALLOWED_MIME } from './preUpload';

function makeFile(name: string, type: string, size: number): File {
  const buf = new Uint8Array(size);
  return new File([buf], name, { type });
}

describe('preCheckFile', () => {
  it('接受 image/jpeg 8MB 以内', () => {
    const f = makeFile('a.jpg', 'image/jpeg', 1024 * 1024);
    const r = preCheckFile(f);
    expect(r.ok).toBe(true);
  });

  it('接受 image/png/webp', () => {
    for (const t of ['image/png', 'image/webp']) {
      const r = preCheckFile(makeFile('a', t, 100));
      expect(r.ok).toBe(true);
    }
  });

  it('拒绝 image/heic 与 application/pdf', () => {
    for (const t of ['image/heic', 'application/pdf']) {
      const r = preCheckFile(makeFile('a', t, 100));
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.code).toBe('UNSUPPORTED');
    }
  });

  it('拒绝超过 8MB', () => {
    const f = makeFile('big.jpg', 'image/jpeg', MAX_UPLOAD_BYTES + 1);
    const r = preCheckFile(f);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.code).toBe('PAYLOAD_TOO_LARGE');
  });

  it('暴露白名单常量,便于 UI 提示', () => {
    expect(ALLOWED_MIME).toContain('image/jpeg');
    expect(MAX_UPLOAD_BYTES).toBe(8 * 1024 * 1024);
  });
});
