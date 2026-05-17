const BASE_URL = import.meta.env.VITE_API_BASE ?? '';

export interface WorldSprite {
  entity_id: string;
  sprites: {
    default: string;
    blink: string;
    mouth_a: string;
    mouth_b: string;
    mouth_c: string;
  };
  position_x: number;
  position_y: number;
}

export type WorldEvent =
  | { type: 'scene_bible_ready'; bible: any }
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
    console.log('[WorldClient] event:', event.type, event);
    for (const cb of this._listeners) cb(event);
  }

  async connect() {
    this._abort = new AbortController();
    const url = `${BASE_URL}/api/world/${this._worldId}`;
    console.log('[WorldClient] connecting to', url);
    try {
      const resp = await fetch(url, { signal: this._abort.signal });
      console.log('[WorldClient] response status:', resp.status);
      if (!resp.ok || !resp.body) {
        this._emit({ type: 'error', message: `World fetch failed: ${resp.status}` });
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('[WorldClient] stream done');
          break;
        }
        const chunk = decoder.decode(value, { stream: true });
        console.log('[WorldClient] raw chunk:', chunk.substring(0, 200));
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        for (const line of lines) {
          if (line.startsWith(':') || line === '') {
            // SSE comment or blank line — skip
          } else if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            console.log('[WorldClient] event:', eventType, data.substring(0, 100));
            try {
              const parsed = JSON.parse(data);
              switch (eventType) {
                case 'scene_bible_ready':
                  this._emit({ type: 'scene_bible_ready', bible: parsed });
                  break;
                case 'npc_sprite_ready':
                  this._emit({ type: 'npc_sprite_ready', sprite: parsed as WorldSprite });
                  break;
                case 'world_ready':
                  this._emit({ type: 'world_ready' });
                  break;
                case 'error':
                  this._emit({ type: 'error', message: parsed.message || 'unknown' });
                  break;
              }
            } catch {
              console.log('[WorldClient] skip non-JSON event');
            }
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        console.error('[WorldClient] error:', e.message);
        this._emit({ type: 'error', message: e.message || 'SSE failed' });
      }
    }
  }

  disconnect() {
    this._abort?.abort();
    this._listeners.clear();
  }
}
