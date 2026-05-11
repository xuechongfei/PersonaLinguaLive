import { useStudioStore } from '../lib/store';
import PersonaMouth from './PersonaMouth';

interface Props {
  renderedWidth: number;
  renderedHeight: number;
}

export default function SpeakingOverlay({ renderedWidth, renderedHeight }: Props) {
  const selectedObject = useStudioStore((s) => s.selectedObject);
  const isSpeaking = useStudioStore((s) => s.isSpeaking);
  const analyserNode = useStudioStore((s) => s.analyserNode);

  if (!selectedObject || renderedWidth <= 0 || renderedHeight <= 0) return null;

  const { x, y, w, h } = selectedObject.bbox;
  const pixelX = x * renderedWidth;
  const pixelY = y * renderedHeight;
  const pixelW = w * renderedWidth;
  const pixelH = h * renderedHeight;

  const mouthSize = Math.min(pixelW, pixelH) * 0.6;

  if (mouthSize < 60) return null;

  const mouthX = pixelX + (pixelW - mouthSize) / 2;
  const mouthY = pixelY - mouthSize * 0.3;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={renderedWidth}
      height={renderedHeight}
      viewBox={`0 0 ${renderedWidth} ${renderedHeight}`}
    >
      <foreignObject
        x={mouthX}
        y={mouthY}
        width={mouthSize}
        height={mouthSize}
      >
        <PersonaMouth
          isSpeaking={isSpeaking}
          analyserNode={analyserNode}
          size={mouthSize}
        />
      </foreignObject>
    </svg>
  );
}
