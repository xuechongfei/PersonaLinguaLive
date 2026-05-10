export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
export const ALLOWED_MIME = ['image/jpeg', 'image/png', 'image/webp'] as const;

export type PreCheckResult =
  | { ok: true }
  | { ok: false; code: 'UNSUPPORTED' | 'PAYLOAD_TOO_LARGE'; message: string };

export function preCheckFile(file: File): PreCheckResult {
  if (!ALLOWED_MIME.includes(file.type as (typeof ALLOWED_MIME)[number])) {
    return {
      ok: false,
      code: 'UNSUPPORTED',
      message: `仅支持 JPEG / PNG / WebP,你给的是 ${file.type || '未知类型'}。`,
    };
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return {
      ok: false,
      code: 'PAYLOAD_TOO_LARGE',
      message: `图片不能大于 ${(MAX_UPLOAD_BYTES / 1024 / 1024).toFixed(0)}MB。`,
    };
  }
  return { ok: true };
}
