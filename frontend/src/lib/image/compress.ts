export interface CompressOptions {
  maxEdge: number;
  sizeThresholdBytes: number;
  quality?: number;
}

const DEFAULTS: Required<CompressOptions> = {
  maxEdge: 1600,
  sizeThresholdBytes: 1_500_000,
  quality: 0.82,
};

export async function compressIfNeeded(
  file: File,
  opts: Partial<CompressOptions> = {},
): Promise<File> {
  const cfg = { ...DEFAULTS, ...opts };

  if (file.size <= cfg.sizeThresholdBytes) return file;

  const dataUrl = await readAsDataURL(file);
  const img = await loadImage(dataUrl);

  const longest = Math.max(img.width, img.height);
  const scale = longest > cfg.maxEdge ? cfg.maxEdge / longest : 1;
  const w = Math.round(img.width * scale);
  const h = Math.round(img.height * scale);

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  if (!ctx) return file;
  ctx.drawImage(img, 0, 0, w, h);

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, 'image/jpeg', cfg.quality),
  );
  if (!blob || blob.size >= file.size) return file;

  const newName = file.name.replace(/\.(png|webp|jpe?g)$/i, '') + '.jpg';
  return new File([blob], newName, { type: 'image/jpeg' });
}

function readAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(reader.error ?? new Error('read failed'));
    reader.readAsDataURL(file);
  });
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('image decode failed'));
    img.src = src;
  });
}
