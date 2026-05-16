import { useEffect, useRef, useState, type SyntheticEvent } from 'react';

export interface ImageReadyInfo {
  naturalWidth: number;
  naturalHeight: number;
  renderedWidth: number;
  renderedHeight: number;
}

interface Props { file: File; alt: string; onReady?: (info: ImageReadyInfo) => void; }

export default function ImageCanvas({ file, alt, onReady }: Props) {
  const [src, setSrc] = useState<string>('');
  const [loaded, setLoaded] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setSrc(url);
    setLoaded(false);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handleLoad(_e: SyntheticEvent<HTMLImageElement>) {
    setLoaded(true);
    // Defer dimension read to ensure layout is complete (clientWidth can be 0
    // if onLoad fires before the browser has laid out the element).
    requestAnimationFrame(() => {
      const img = imgRef.current;
      if (!img || !onReady) return;
      const rect = img.getBoundingClientRect();
      const rw = rect.width || img.clientWidth || img.naturalWidth;
      const rh = rect.height || img.clientHeight || img.naturalHeight;
      onReady({
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        renderedWidth: Math.round(rw),
        renderedHeight: Math.round(rh),
      });
    });
  }

  if (!src) return null;

  return (
    <div className="relative">
      {!loaded && (
        <div className="skeleton w-full h-64 rounded-3xl" />
      )}
      <img
        ref={imgRef}
        src={src}
        alt={alt}
        onLoad={handleLoad}
        className={`block max-w-full h-auto rounded-3xl shadow-card transition-opacity duration-500 ${loaded ? 'opacity-100' : 'opacity-0 absolute inset-0'}`}
      />
    </div>
  );
}
