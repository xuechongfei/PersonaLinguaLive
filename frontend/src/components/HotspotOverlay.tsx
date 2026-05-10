import type { DetectedObject } from '../lib/api';

interface Props {
  renderedWidth: number;
  renderedHeight: number;
  objects: DetectedObject[];
  onSelect: (obj: DetectedObject) => void;
}

export default function HotspotOverlay({
  renderedWidth,
  renderedHeight,
  objects,
  onSelect,
}: Props) {
  if (renderedWidth <= 0 || renderedHeight <= 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={renderedWidth}
      height={renderedHeight}
      viewBox={`0 0 ${renderedWidth} ${renderedHeight}`}
    >
      {objects.map((obj) => {
        const x = obj.bbox.x * renderedWidth;
        const y = obj.bbox.y * renderedHeight;
        const w = obj.bbox.w * renderedWidth;
        const h = obj.bbox.h * renderedHeight;
        return (
          <g key={obj.id} className="pointer-events-auto">
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill="rgba(56,189,248,0.12)"
              stroke="rgb(2,132,199)"
              strokeWidth={2}
              rx={6}
              role="button"
              aria-label={obj.label}
              tabIndex={0}
              style={{ cursor: 'pointer' }}
              onClick={() => onSelect(obj)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onSelect(obj);
              }}
            />
            <text
              x={x + 6}
              y={y + 18}
              fill="rgb(15,23,42)"
              style={{
                font: '600 12px ui-sans-serif, system-ui, sans-serif',
                paintOrder: 'stroke',
                stroke: 'white',
                strokeWidth: 3,
              }}
              pointerEvents="none"
            >
              {obj.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
