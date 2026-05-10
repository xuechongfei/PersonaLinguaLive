import { useEffect, useRef } from 'react';

interface Props {
  isSpeaking: boolean;
  analyserNode?: AnalyserNode;
}

export default function PersonaMouth({ isSpeaking, analyserNode }: Props) {
  const mouthRef = useRef<SVGEllipseElement>(null);

  useEffect(() => {
    const mouth = mouthRef.current;
    if (!mouth) return;

    if (!isSpeaking) {
      mouth.setAttribute('ry', '4');
      return;
    }

    if (analyserNode) {
      // Use Web Audio API AnalyserNode to drive mouth
      const dataArray = new Uint8Array(analyserNode.frequencyBinCount);
      let animId: number;

      const animate = () => {
        analyserNode.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        // Normalize avg (0-255) to mouth height (4-16)
        const ry = 4 + (avg / 255) * 12;
        mouth.setAttribute('ry', String(ry));
        animId = requestAnimationFrame(animate);
      };

      animate();
      return () => cancelAnimationFrame(animId);
    }

    // Fallback: CSS-like pulse animation via rAF
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

  return (
    <svg
      viewBox="0 0 120 120"
      className="w-28 h-28"
      role="img"
      aria-label={isSpeaking ? 'Persona is speaking' : 'Persona is silent'}
    >
      {/* Face circle */}
      <circle cx="60" cy="60" r="55" fill="#FFF3E0" stroke="#FFB74D" strokeWidth="2" />
      {/* Left eye */}
      <circle cx="40" cy="45" r="5" fill="#333" />
      {/* Right eye */}
      <circle cx="80" cy="45" r="5" fill="#333" />
      {/* Mouth */}
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
