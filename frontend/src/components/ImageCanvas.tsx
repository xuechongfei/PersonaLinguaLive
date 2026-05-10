import { useEffect, useRef, useState, type SyntheticEvent } from 'react';

export interface ImageReadyInfo {
  naturalWidth: number;
  naturalHeight: number;
  renderedWidth: number;
  renderedHeight: number;
}

interface Props {
  file: File;
  alt: string;
  onReady?: (info: ImageReadyInfo) => void;
}

export default function ImageCanvas({ file, alt, onReady }: Props) {
  const [src, setSrc] = useState<string>('');
  const imgRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setSrc(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handleLoad(_e: SyntheticEvent<HTMLImageElement>) {
    const img = imgRef.current;
    if (!img || !onReady) return;
    onReady({
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      renderedWidth: img.clientWidth,
      renderedHeight: img.clientHeight,
    });
  }

  if (!src) return null;
  return (
    <img
      ref={imgRef}
      src={src}
      alt={alt}
      onLoad={handleLoad}
      className="block max-w-full h-auto rounded-xl shadow"
    />
  );
}
