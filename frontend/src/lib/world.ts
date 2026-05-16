const BASE_URL = import.meta.env.VITE_API_BASE ?? '';

export interface WorldSprite {
  entity_id: string;
  sprites: {
    default: string;   // base64 png
    blink: string;
    mouth_a: string;
    mouth_b: string;
    mouth_c: string;
  };
  position_x: number;  // 0-1 normalized
  position_y: number;
}

export type WorldEvent =
  | { type: 'scene_bible_ready'; bible: any }
  | { type: 'background_ready'; imageBase64: string }
  | { type: 'npc_sprite_ready'; sprite: WorldSprite }
  | { type: 'world_ready' }
  | { type: 'error'; message: string };

type EventCallback = (event: WorldEvent) => void;

export class WorldClient {
  private _worldId: string;
  private _abort: AbortController | null = null;
  private _listeners: Set<EventCallback> = new Set();

  constructor(worldId: string) {
    this._worldId = worldId;
  }

  on(cb: EventCallback) {
    this._listeners.add(cb);
  }

  off(cb: EventCallback) {
    this._listeners.delete(cb);
  }

  private _emit(event: WorldEvent) {
    for (const cb of this._listeners) cb(event);
  }

  async connect() {
    this._abort = new AbortController();
    try {
      const resp = await fetch(`${BASE_URL}/api/world/${this._worldId}`, {
        signal: this._abort.signal,
      });
      if (!resp.ok || !resp.body) {
        this._emit({ type: 'error', message: `World fetch failed: ${resp.status}` });
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        let data = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            data = line.slice(6);
            this._handleEvent(eventType, data);
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        this._emit({ type: 'error', message: e.message || 'SSE connection failed' });
      }
    }
  }

  private _handleEvent(type: string, raw: string) {
    try {
      const data = JSON.parse(raw);
      switch (type) {
        case 'scene_bible_ready':
          this._emit({ type: 'scene_bible_ready', bible: data });
          break;
        case 'background_ready':
          this._emit({ type: 'background_ready', imageBase64: data.image_base64 || '' });
          break;
        case 'npc_sprite_ready':
          this._emit({ type: 'npc_sprite_ready', sprite: data as WorldSprite });
          break;
        case 'world_ready':
          this._emit({ type: 'world_ready' });
          break;
        case 'error':
          this._emit({ type: 'error', message: data.message || 'unknown' });
          break;
      }
    } catch {
      // non-JSON event, skip
    }
  }

  disconnect() {
    this._abort?.abort();
    this._listeners.clear();
  }
}
