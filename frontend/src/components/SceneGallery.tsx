import { useState } from 'react';

interface SceneMeta {
  id: string;
  name: string;
  filename: string;
  description: string;
  emoji: string;
}

const SCENES: SceneMeta[] = [
  { id: 'kitchen', name: 'Kitchen', filename: 'kitchen.webp', description: 'Counter with appliances and utensils', emoji: '\u{1F373}' },
  { id: 'desk', name: 'Study Desk', filename: 'desk.webp', description: 'Laptop, books, stationery, coffee mug', emoji: '\u{1F4DA}' },
  { id: 'living-room', name: 'Living Room', filename: 'living-room.webp', description: 'Sofa, TV, plants, bookshelf', emoji: '\u{1F3A0}' },
  { id: 'cafe', name: 'Cafe', filename: 'cafe.webp', description: 'Coffee cup, pastry, newspaper, laptop', emoji: '☕' },
  { id: 'park', name: 'Park', filename: 'park.webp', description: 'Bench, tree, bicycle, fountain', emoji: '\u{1F333}' },
  { id: 'bedroom', name: 'Bedroom', filename: 'bedroom.webp', description: 'Bed, wardrobe, mirror, lamp', emoji: '\u{1F6CF}' },
];

interface Props {
  onSelectScene: (file: File) => void;
}

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
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold text-slate-500 mb-3">Or pick a built-in scene</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {SCENES.map((scene) => (
          <button
            key={scene.id}
            type="button"
            onClick={() => handleSelect(scene)}
            disabled={loading === scene.id}
            className="rounded-xl border border-slate-200 bg-white p-3 text-left hover:border-sky-400 hover:shadow transition disabled:opacity-50"
          >
            <div className="text-lg mb-1">{scene.emoji}</div>
            <p className="font-medium text-sm text-slate-800">{scene.name}</p>
            <p className="text-xs text-slate-400 mt-0.5">{scene.description}</p>
            {loading === scene.id && (
              <p className="text-xs text-sky-600 mt-1">Loading...</p>
            )}
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-rose-600">{error}</p>
      )}
    </div>
  );
}
