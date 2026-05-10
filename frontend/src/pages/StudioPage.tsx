import { useState } from 'react';
import UploadZone from '../components/UploadZone';
import ImageCanvas, { type ImageReadyInfo } from '../components/ImageCanvas';
import HotspotOverlay from '../components/HotspotOverlay';
import PersonaPlaceholderPanel from '../components/PersonaPlaceholderPanel';
import { analyzeImage, ApiError, type DetectedObject, type VisionAnalyzeResponse } from '../lib/api';
import { compressIfNeeded } from '../lib/image/compress';

type Status =
  | { kind: 'idle' }
  | { kind: 'analyzing' }
  | { kind: 'ready'; result: VisionAnalyzeResponse }
  | { kind: 'error'; message: string };

export default function StudioPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>({ kind: 'idle' });
  const [size, setSize] = useState<ImageReadyInfo | null>(null);
  const [selected, setSelected] = useState<DetectedObject | null>(null);

  async function handleFile(raw: File) {
    setSelected(null);
    setSize(null);
    setStatus({ kind: 'analyzing' });
    try {
      const slim = await compressIfNeeded(raw);
      setFile(slim);
      const result = await analyzeImage(slim);
      setStatus({ kind: 'ready', result });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : '出了点问题,请重试。';
      setStatus({ kind: 'error', message: msg });
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <h1 className="text-2xl font-semibold text-center">Studio</h1>
      <p className="mt-1 mb-6 text-center text-sm text-slate-500">
        选一张照片,看 AI 标出能开口说话的对象。
      </p>

      {!file && <UploadZone onFile={handleFile} />}

      {file && (
        <section className="mx-auto mt-4 w-full max-w-3xl">
          <div className="relative inline-block">
            <ImageCanvas file={file} alt="待分析的图片" onReady={setSize} />
            {status.kind === 'ready' && size && (
              <HotspotOverlay
                renderedWidth={size.renderedWidth}
                renderedHeight={size.renderedHeight}
                objects={status.result.objects}
                onSelect={setSelected}
              />
            )}
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-white"
              onClick={() => {
                setFile(null);
                setStatus({ kind: 'idle' });
                setSelected(null);
                setSize(null);
              }}
            >
              换一张
            </button>
            {status.kind === 'analyzing' && (
              <span className="text-sm text-slate-500">分析中…</span>
            )}
            {status.kind === 'ready' && (
              <span className="text-sm text-slate-500">
                共识别 {status.result.objects.length} 个对象
              </span>
            )}
          </div>

          {status.kind === 'error' && (
            <p role="alert" className="mt-4 text-sm text-rose-600">
              {status.message}
            </p>
          )}
        </section>
      )}

      {selected && (
        <PersonaPlaceholderPanel object={selected} onClose={() => setSelected(null)} />
      )}
    </main>
  );
}
