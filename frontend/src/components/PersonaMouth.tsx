import { useEffect, useRef } from 'react';

interface Props {
  isSpeaking: boolean;
  analyserNode?: AnalyserNode;
  size?: number;
  className?: string;
}

const EYE_RADIUS_OPEN = 5;
const EYE_RADIUS_CLOSED = 0.5;
const EYE_RADIUS_WIDE = 7;
const EYE_BASE_LEFT = { cx: 40, cy: 45 };
const EYE_BASE_RIGHT = { cx: 80, cy: 45 };

export default function PersonaMouth({ isSpeaking, analyserNode, size = 112, className }: Props) {
  const mouthRef = useRef<SVGEllipseElement>(null);
  const leftEyeRef = useRef<SVGCircleElement>(null);
  const rightEyeRef = useRef<SVGCircleElement>(null);

  // Mouth animation (unchanged logic)
  useEffect(() => {
    const mouth = mouthRef.current;
    if (!mouth) return;

    if (!isSpeaking) {
      mouth.setAttribute('ry', '4');
      return;
    }

    if (analyserNode) {
      const dataArray = new Uint8Array(analyserNode.frequencyBinCount);
      let animId: number;

      const animate = () => {
        analyserNode.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        const ry = 4 + (avg / 255) * 12;
        mouth.setAttribute('ry', String(ry));
        animId = requestAnimationFrame(animate);
      };

      animate();
      return () => cancelAnimationFrame(animId);
    }

    let direction = 1;
    let currentRy = 4;
    let animId: number;

    const animate = () => {
      currentRy += direction * 0.5;
      if (currentRy >= 16) direction = -1;
      if (currentRy <= 4) direction = 1;
      mouth.setAttribute('ry', String(currentRy));
      animId = requestAnimationFrame(animate);
    };

    animate();
    return () => cancelAnimationFrame(animId);
  }, [isSpeaking, analyserNode]);

  // Eye widening when speaking
  useEffect(() => {
    const left = leftEyeRef.current;
    const right = rightEyeRef.current;
    if (!left || !right) return;

    const r = isSpeaking ? EYE_RADIUS_WIDE : EYE_RADIUS_OPEN;
    left.setAttribute('r', String(r));
    right.setAttribute('r', String(r));
  }, [isSpeaking]);

  // Blink animation
  useEffect(() => {
    const left = leftEyeRef.current;
    const right = rightEyeRef.current;
    if (!left || !right) return;

    let timeoutId: ReturnType<typeof setTimeout>;

    const scheduleBlink = () => {
      const minInterval = isSpeaking ? 800 : 2000;
      const maxInterval = isSpeaking ? 2000 : 5000;
      const delay = minInterval + Math.random() * (maxInterval - minInterval);

      timeoutId = setTimeout(() => {
        left.setAttribute('r', String(EYE_RADIUS_CLOSED));
        right.setAttribute('r', String(EYE_RADIUS_CLOSED));

        setTimeout(() => {
          const openR = isSpeaking ? EYE_RADIUS_WIDE : EYE_RADIUS_OPEN;
          left.setAttribute('r', String(openR));
          right.setAttribute('r', String(openR));
          scheduleBlink();
        }, 150);
      }, delay);
    };

    scheduleBlink();
    return () => clearTimeout(timeoutId);
  }, [isSpeaking]);

  // Gaze drift
  useEffect(() => {
    const left = leftEyeRef.current;
    const right = rightEyeRef.current;
    if (!left || !right) return;

    const offset = { x: 0, y: 0 };
    const target = { x: 0, y: 0 };
    let animId: number;
    let driftTimeout: ReturnType<typeof setTimeout>;

    const pickNewTarget = () => {
      target.x = (Math.random() - 0.5) * 6;
      target.y = (Math.random() - 0.5) * 6;
      driftTimeout = setTimeout(pickNewTarget, 3000 + Math.random() * 2000);
    };

    const animate = () => {
      const lerp = 0.05;
      offset.x += (target.x - offset.x) * lerp;
      offset.y += (target.y - offset.y) * lerp;

      left.setAttribute('cx', String(EYE_BASE_LEFT.cx + offset.x));
      left.setAttribute('cy', String(EYE_BASE_LEFT.cy + offset.y));
      right.setAttribute('cx', String(EYE_BASE_RIGHT.cx + offset.x));
      right.setAttribute('cy', String(EYE_BASE_RIGHT.cy + offset.y));

      animId = requestAnimationFrame(animate);
    };

    pickNewTarget();
    animate();

    return () => {
      cancelAnimationFrame(animId);
      clearTimeout(driftTimeout);
    };
  }, []);

  return (
    <svg
      viewBox="0 0 120 120"
      className={className}
      style={{ width: size, height: size }}
      role="img"
      aria-label={isSpeaking ? 'Persona is speaking' : 'Persona is silent'}
    >
      <circle cx="60" cy="60" r="55" fill="#FFF3E0" stroke="#FFB74D" strokeWidth="2" />
      <circle ref={leftEyeRef} cx={40} cy={45} r={5} fill="#333" />
      <circle ref={rightEyeRef} cx={80} cy={45} r={5} fill="#333" />
      <ellipse
        ref={mouthRef}
        cx="60"
        cy="75"
        rx="15"
        ry="4"
        fill="#E57373"
      />
    </svg>
  );
}
