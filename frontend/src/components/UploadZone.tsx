import { useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { preCheckFile } from '../lib/safety/preUpload';

interface Props {
  onFile: (file: File) => void;
}

export default function UploadZone({ onFile }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [hover, setHover] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function accept(file: File | undefined) {
    if (!file) return;
    setError(null);
    const r = preCheckFile(file);
    if (!r.ok) {
      setError(r.message);
      return;
    }
    onFile(file);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    accept(e.target.files?.[0]);
    e.target.value = '';
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setHover(false);
    accept(e.dataTransfer.files?.[0]);
  }

  function onDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setHover(true);
  }

  function onDragLeave() {
    setHover(false);
  }

  const base =
    'flex flex-col items-center justify-center gap-3 w-full max-w-xl mx-auto rounded-2xl border-2 border-dashed p-10 cursor-pointer transition-colors';
  const tone = hover ? 'border-sky-500 bg-sky-50' : 'border-slate-300 bg-white hover:bg-slate-50';

  return (
    <div className="w-full">
      <div
        data-testid="upload-zone"
        className={`${base} ${tone}`}
        onClick={() => inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
        }}
      >
        <p className="text-lg font-medium text-slate-800">把图片拖到这里,或点击选择文件</p>
        <p className="text-sm text-slate-500">支持 JPEG / PNG / WebP,单张 ≤ 8MB</p>
        <input
          ref={inputRef}
          data-testid="upload-input"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={onChange}
        />
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm text-rose-600 text-center">
          {error}
        </p>
      )}
    </div>
  );
}
