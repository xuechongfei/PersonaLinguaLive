import { useState } from 'react';

interface SceneMeta {
  id: string;
  name: string;
  filename: string;
  description: string;
  emoji: string;
}

const SCENES: SceneMeta[] = [
  { id: 'kitchen', name: 'Kitchen', filename: 'kitchen.webp', description: 'Counter with appliances', emoji: '\u{1F373}' },
  { id: 'desk', name: 'Study Desk', filename: 'desk.webp', description: 'Laptop, books, coffee', emoji: '\u{1F4DA}' },
  { id: 'living-room', name: 'Living Room', filename: 'living-room.webp', description: 'Sofa, TV, plants', emoji: '\u{1F3A0}' },
  { id: 'cafe', name: 'Cafe', filename: 'cafe.webp', description: 'Coffee, pastry, laptop', emoji: '☕' },
  { id: 'park', name: 'Park', filename: 'park.webp', description: 'Bench, tree, fountain', emoji: '\u{1F333}' },
  { id: 'bedroom', name: 'Bedroom', filename: 'bedroom.webp', description: 'Bed, wardrobe, lamp', emoji: '\u{1F6CF}' },
];

interface Props { onSelectScene: (file: File) => void; }

export default function SceneGallery({ onSelectScene }: Props) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSelect(scene: SceneMeta) {
    setError(null);
    setLoading(scene.id);
    try {
      const resp = await fetch(`/scenes/${scene.filename}`);
      if (!resp.ok) throw new Error(`Failed to load scene: ${resp.status}`);
      const blob = await resp.blob();
      const file = new File([blob], scene.filename, { type: 'image/webp' });
      onSelectScene(file);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load scene');
    } finally { setLoading(null); }
  }

  return (
    <div className="mt-8">
      <h3 className="text-xs font-semibold text-ink-light uppercase tracking-wider mb-3">
        Or pick a built-in scene
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {SCENES.map((scene) => (
          <button
            key={scene.id}
            type="button"
            onClick={() => handleSelect(scene)}
            disabled={loading === scene.id}
            className="card-hover text-left p-4 disabled:opacity-50"
          >
            <span className="text-2xl">{scene.emoji}</span>
            <p className="mt-2 font-semibold text-sm text-ink">{scene.name}</p>
            <p className="text-xs text-ink-light mt-0.5">{scene.description}</p>
            {loading === scene.id && (
              <span className="inline-block mt-1.5 w-3 h-3 rounded-full border-2 border-honey border-t-transparent animate-spin" />
            )}
          </button>
        ))}
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-rose font-medium">{error}</p>}
    </div>
  );
}
