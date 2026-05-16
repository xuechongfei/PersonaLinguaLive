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
      {objects.map((obj) => {
        const x = obj.bbox.x * renderedWidth;
        const y = obj.bbox.y * renderedHeight;
        const w = obj.bbox.w * renderedWidth;
        const h = obj.bbox.h * renderedHeight;
        return (
          <g key={obj.id} className="pointer-events-auto">
            {/* Glow ring */}
            <rect
              x={x - 3}
              y={y - 3}
              width={w + 6}
              height={h + 6}
              fill="none"
              stroke="url(#glowGradient)"
              strokeWidth={2.5}
              rx={10}
              className="opacity-70 hover:opacity-100 transition-opacity duration-300"
              style={{ filter: 'url(#blurFilter)' }}
            />
            {/* Clickable area */}
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill="rgba(251, 191, 36, 0.1)"
              stroke="rgba(217, 119, 6, 0.45)"
              strokeWidth={2}
              rx={8}
              role="button"
              aria-label={obj.label}
              tabIndex={0}
              className="cursor-pointer transition-all duration-200 hover:fill-[rgba(251,191,36,0.2)]"
              style={{ cursor: 'pointer' }}
              onClick={() => onSelect(obj)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onSelect(obj);
              }}
            />
            {/* Label pill */}
            <foreignObject
              x={Math.max(0, x + w / 2 - 40)}
              y={y - 28}
              width={Math.min(renderedWidth, 80)}
              height={24}
              pointerEvents="none"
            >
              <div className="flex items-center justify-center w-full">
                <span
                  className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold
                             bg-white/90 backdrop-blur-sm text-honey-dark
                             shadow-sm border border-honey-light/50
                             whitespace-nowrap"
                >
                  {obj.label}
                </span>
              </div>
            </foreignObject>
          </g>
        );
      })}

      {/* SVG filters */}
      <defs>
        <linearGradient id="glowGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FBBF24" />
          <stop offset="100%" stopColor="#D97706" />
        </linearGradient>
        <filter id="blurFilter" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" />
        </filter>
      </defs>
    </svg>
  );
}
