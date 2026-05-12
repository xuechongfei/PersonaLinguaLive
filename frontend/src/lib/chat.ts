import type { LearnerContext } from './learnerContext';

const BASE_URL = import.meta.env.VITE_API_BASE ?? '';

export type ChatEventType = 'text_chunk' | 'speak_text' | 'audio' | 'result' | 'error';

export interface ChatEvent {
  type: ChatEventType;
  content?: string;
  segments?: { speak: string; learning: string; followup: string };
  audio_base64?: string;
  message?: string;
}

type EventHandler = (event: ChatEvent) => void;

export class ChatClient {
  private ws: WebSocket | null = null;
  private handlers: Map<ChatEventType, Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private sessionId: string = '';
  private systemMessage: object = {};
  private userLevel: string = 'beginner';
  private learnerContext: LearnerContext | null = null;
  private voiceId: string | null = null;

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  on(event: ChatEventType, handler: EventHandler): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  off(event: ChatEventType, handler: EventHandler): void {
    this.handlers.get(event)?.delete(handler);
  }

  private emit(event: ChatEvent): void {
    const handlers = this.handlers.get(event.type);
    if (handlers) {
      handlers.forEach((h) => h(event));
    }
  }

  connect(
    sessionId: string,
    systemMessage: object,
    userLevel: string = 'beginner',
    learnerContext: LearnerContext | null = null,
    voiceId: string | null = null,
  ): void {
    this.sessionId = sessionId;
    this.systemMessage = systemMessage;
    this.userLevel = userLevel;
    this.learnerContext = learnerContext;
    this.voiceId = voiceId;
    this._connect();
  }

  private _connect(): void {
    // Determine WebSocket URL from HTTP base URL
    const base = BASE_URL.replace(/^http/, 'ws');
    const url = `${base}/api/chat`;

    this.ws = new WebSocket(url);
    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      // Send init frame
      this.ws!.send(JSON.stringify({
        type: 'init',
        session_id: this.sessionId,
        system_message: this.systemMessage,
        user_level: this.userLevel,
        ...(this.voiceId ? { voice_id: this.voiceId } : {}),
        ...(this.learnerContext ? { learner_context: this.learnerContext } : {}),
      }));
    };

    this.ws.onmessage = (msg: MessageEvent) => {
      try {
        const event: ChatEvent = JSON.parse(msg.data);
        this.emit(event);
      } catch {
        // Ignore non-JSON messages
      }
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = Math.pow(2, this.reconnectAttempts) * 1000;
        this.reconnectAttempts++;
        this.reconnectTimeout = setTimeout(() => this._connect(), delay);
      } else {
        this.emit({ type: 'error', message: 'Connection lost. Please refresh.' });
      }
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror, so reconnection is handled there
    };
  }

  sendMessage(content: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'user_message', content }));
    } else {
      this.emit({ type: 'error', message: 'Not connected to chat server.' });
    }
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.ws?.close();
    this.ws = null;
    this.reconnectAttempts = 0;
  }
}
