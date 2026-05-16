import type { Entity } from '../lib/api';

interface Props {
  renderedWidth: number;
  renderedHeight: number;
  objects: Entity[];
  onSelect: (obj: Entity) => void;
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
      <defs>
        <linearGradient id="glowGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FBBF24" />
          <stop offset="100%" stopColor="#D97706" />
        </linearGradient>
        <filter id="blurFilter" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" />
        </filter>
      </defs>

      {objects.map((obj) => {
        const x = obj.bbox.x * renderedWidth;
        const y = obj.bbox.y * renderedHeight;
        const w = obj.bbox.w * renderedWidth;
        const h = obj.bbox.h * renderedHeight;

        // Label position: inside the box at top-left if box is tall enough, otherwise above
        const labelInside = h >= 40;
        const labelX = Math.min(Math.max(x + 6, 0), renderedWidth - 90);
        const labelY = labelInside ? y + 6 : Math.max(y - 26, 2);

        return (
          <g key={obj.id} className="pointer-events-auto">
            {/* Glow ring — visible when hovering */}
            <rect
              x={x - 4}
              y={y - 4}
              width={w + 8}
              height={h + 8}
              fill="none"
              stroke="url(#glowGradient)"
              strokeWidth={3}
              rx={12}
              className="opacity-0 hover:opacity-100 transition-opacity duration-300"
              style={{ filter: 'url(#blurFilter)' }}
            />
            {/* Solid border — always visible */}
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill="rgba(251, 191, 36, 0.18)"
              stroke="#D97706"
              strokeWidth={2.5}
              strokeDasharray="8 4"
              rx={10}
              className="transition-all duration-200 hover:fill-[rgba(251,191,36,0.35)]"
              style={{ cursor: 'pointer' }}
            />
            {/* Clickable area — full opacity for click capture */}
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill="transparent"
              rx={10}
              role="button"
              aria-label={obj.label}
              tabIndex={0}
              style={{ cursor: 'pointer' }}
              onClick={() => onSelect(obj)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onSelect(obj);
              }}
            />
            {/* Label pill */}
            <foreignObject
              x={labelX}
              y={labelY}
              width={84}
              height={24}
              pointerEvents="none"
            >
              <div className="flex items-center">
                <span
                  className="inline-block px-2.5 py-0.5 rounded-full text-xs font-bold
                             bg-amber-500 text-white shadow-md
                             whitespace-nowrap"
                >
                  {obj.label}
                </span>
              </div>
            </foreignObject>
          </g>
        );
      })}
    </svg>
  );
}
