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
    if (!r.ok) { setError(r.message); return; }
    onFile(file);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    accept(e.target.files?.[0]);
    e.target.value = '';
  }

  function onDrop(e: DragEvent<HTMLDivElement>) { e.preventDefault(); setHover(false); accept(e.dataTransfer.files?.[0]); }
  function onDragOver(e: DragEvent<HTMLDivElement>) { e.preventDefault(); setHover(true); }
  function onDragLeave() { setHover(false); }

  return (
    <div className="w-full">
      <div
        data-testid="upload-zone"
        className={`flex flex-col items-center justify-center gap-4 w-full max-w-xl mx-auto
          rounded-3xl border-2 border-dashed p-12 cursor-pointer transition-all duration-300
          ${hover
            ? 'border-honey bg-honey-light/10 scale-[1.02] shadow-glow'
            : 'border-sand bg-white/60 hover:border-honey/40 hover:bg-white'}`}
        onClick={() => inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
      >
        <span className="text-4xl">{'\u{1F4F7}'}</span>
        <div className="text-center">
          <p className="text-base font-semibold text-ink">Drop your photo here</p>
          <p className="mt-1 text-sm text-ink-light">or click to browse — JPEG / PNG / WebP, max 8MB</p>
        </div>
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
        <p role="alert" className="mt-3 text-sm text-rose text-center font-medium">{error}</p>
      )}
    </div>
  );
}
