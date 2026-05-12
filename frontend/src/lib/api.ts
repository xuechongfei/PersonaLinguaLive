export interface HealthPayload {
  status: 'ok';
  app: string;
  version: string;
  environment: 'development' | 'production' | 'test';
}

const BASE_URL = import.meta.env.VITE_API_BASE ?? '';

export async function fetchHealth(): Promise<HealthPayload> {
  const resp = await fetch(`${BASE_URL}/healthz`);
  if (!resp.ok) {
    throw new Error(`Health check failed with status ${resp.status}`);
  }
  return (await resp.json()) as HealthPayload;
}

export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DetectedObject {
  id: string;
  label: string;
  bbox: BBox;
  confidence: number;
  persona_seed?: string | null;
}

export interface VisionAnalyzeResponse {
  request_id: string;
  is_safe: boolean;
  reject_reasons: string[];
  scene_summary: string;
  objects: DetectedObject[];
}

export type ApiErrorCode =
  | 'INVALID_INPUT'
  | 'PAYLOAD_TOO_LARGE'
  | 'UNSUPPORTED_MEDIA'
  | 'UNSAFE_IMAGE'
  | 'RATE_LIMITED'
  | 'UPSTREAM_FAILURE'
  | 'UPSTREAM_TIMEOUT'
  | 'NETWORK'
  | 'UNKNOWN';

export class ApiError extends Error {
  code: ApiErrorCode;
  status: number;
  retryAfter?: number;
  rejectReasons?: string[];

  constructor(opts: {
    code: ApiErrorCode;
    message: string;
    status: number;
    retryAfter?: number;
    rejectReasons?: string[];
  }) {
    super(opts.message);
    this.code = opts.code;
    this.status = opts.status;
    this.retryAfter = opts.retryAfter;
    this.rejectReasons = opts.rejectReasons;
  }
}

export async function analyzeImage(file: File): Promise<VisionAnalyzeResponse> {
  const fd = new FormData();
  fd.append('image', file);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/vision/analyze`, { method: 'POST', body: fd });
  } catch {
    throw new ApiError({ code: 'NETWORK', message: '网络异常,请稍后重试。', status: 0 });
  }

  if (res.ok) {
    return (await res.json()) as VisionAnalyzeResponse;
  }

  let body: {
    code?: ApiErrorCode;
    message?: string;
    details?: { retry_after_s?: number; reject_reasons?: string[] };
  } = {};
  try {
    body = await res.json();
  } catch {
    /* ignore: 非 JSON 体走默认 */
  }

  const headerRetry = Number(res.headers.get('Retry-After'));
  const retryAfter =
    body.details?.retry_after_s ??
    (Number.isFinite(headerRetry) && headerRetry > 0 ? headerRetry : undefined);

  throw new ApiError({
    code: body.code ?? 'UNKNOWN',
    message: body.message ?? `请求失败:${res.status}`,
    status: res.status,
    retryAfter,
    rejectReasons: body.details?.reject_reasons,
  });
}

// --- Persona API ---

export interface PersonaGenerateRequest {
  label: string;
  persona_seed?: string;
  scene_summary?: string;
  user_level?: string;
}

export interface PersonaGenerateResponse {
  persona_id: string;
  persona_name: string;
  description: string;
  system_prompt: string;
  vocab_focus: string[];
  voice_id: string;
}

export async function generatePersona(data: PersonaGenerateRequest): Promise<PersonaGenerateResponse> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/persona/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  } catch {
    throw new ApiError({ code: 'NETWORK', message: '网络异常,请稍后重试。', status: 0 });
  }

  if (res.ok) {
    return (await res.json()) as PersonaGenerateResponse;
  }

  let body: { code?: ApiErrorCode; message?: string; details?: { retry_after_s?: number } } = {};
  try { body = await res.json(); } catch { /* ignore */ }

  throw new ApiError({
    code: body.code ?? 'UNKNOWN',
    message: body.message ?? `请求失败:${res.status}`,
    status: res.status,
    retryAfter: body.details?.retry_after_s,
  });
}

// --- Chat Summary API ---

export interface VocabEntry {
  word: string;
  definition: string;
  example: string;
}

export interface ChatSummaryRequest {
  session_id: string;
  user_level?: string;
}

export interface ChatSummaryResponse {
  new_words: VocabEntry[];
  grammar_points: string[];
  fluency_score: number;
  strengths: string[];
  areas_to_improve: string[];
}

export async function fetchSummary(data: ChatSummaryRequest): Promise<ChatSummaryResponse> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/chat/summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  } catch {
    throw new ApiError({ code: 'NETWORK', message: '网络异常,请稍后重试。', status: 0 });
  }

  if (res.ok) {
    return (await res.json()) as ChatSummaryResponse;
  }

  let body: { code?: ApiErrorCode; message?: string } = {};
  try { body = await res.json(); } catch { /* ignore */ }

  throw new ApiError({
    code: body.code ?? 'UNKNOWN',
    message: body.message ?? `请求失败:${res.status}`,
    status: res.status,
  });
}
