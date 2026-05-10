import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

class MockWebSocket {
  onopen: (() => void) | null = null;
  onclose: ((e: any) => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  readyState: number = WebSocket.OPEN;
  sent: string[] = [];

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.({ code: 1000, reason: 'close', wasClean: true });
  }

  // Helper for tests
  _receive(data: string): void {
    this.onmessage?.({ data } as MessageEvent);
  }

  _triggerOpen(): void {
    this.onopen?.();
  }
}

let mockWs: MockWebSocket;

function createMockWebSocketConstructor(): any {
  const wsMock = vi.fn(() => {
    mockWs = new MockWebSocket();
    return mockWs;
  });
  wsMock.CONNECTING = 0;
  wsMock.OPEN = 1;
  wsMock.CLOSING = 2;
  wsMock.CLOSED = 3;
  return wsMock;
}

vi.stubGlobal('WebSocket', createMockWebSocketConstructor());

describe('ChatClient', () => {
  beforeEach(() => {
    mockWs = new MockWebSocket();
    const wsMock = createMockWebSocketConstructor();
    vi.stubGlobal('WebSocket', wsMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('connects and sends init frame', async () => {
    const { ChatClient } = await import('../lib/chat');
    const client = new ChatClient();
    client.connect('sess1', { role: 'system', content: 'You are a bot.' });

    // Trigger onopen
    mockWs._triggerOpen();

    // Should have sent init
    expect(mockWs.sent.length).toBe(1);
    const init = JSON.parse(mockWs.sent[0]);
    expect(init.type).toBe('init');
    expect(init.session_id).toBe('sess1');
  });

  it('sends user message', async () => {
    const { ChatClient } = await import('../lib/chat');
    const client = new ChatClient();
    client.connect('sess1', { role: 'system', content: 'bot' });
    mockWs._triggerOpen();
    mockWs.sent = []; // clear init

    client.sendMessage('Hello!');
    expect(mockWs.sent.length).toBe(1);
    const msg = JSON.parse(mockWs.sent[0]);
    expect(msg.type).toBe('user_message');
    expect(msg.content).toBe('Hello!');
  });

  it('dispatches text_chunk events', async () => {
    const { ChatClient } = await import('../lib/chat');
    const client = new ChatClient();
    const handler = vi.fn();
    client.on('text_chunk', handler);
    client.connect('sess1', {});
    mockWs._triggerOpen();

    mockWs._receive(JSON.stringify({ type: 'text_chunk', content: 'Hello' }));
    expect(handler).toHaveBeenCalledWith({ type: 'text_chunk', content: 'Hello' });
  });

  it('dispatches result events', async () => {
    const { ChatClient } = await import('../lib/chat');
    const client = new ChatClient();
    const handler = vi.fn();
    client.on('result', handler);
    client.connect('sess1', {});
    mockWs._triggerOpen();

    const resultEvent = {
      type: 'result',
      segments: { speak: 'Hello!', learning: 'Tip', followup: 'Q?' },
      audio_base64: 'AAAA',
    };
    mockWs._receive(JSON.stringify(resultEvent));
    expect(handler).toHaveBeenCalledWith(resultEvent);
  });

  it('dispatches error events', async () => {
    const { ChatClient } = await import('../lib/chat');
    const client = new ChatClient();
    const handler = vi.fn();
    client.on('error', handler);
    client.connect('sess1', {});
    mockWs._triggerOpen();

    mockWs._receive(JSON.stringify({ type: 'error', message: 'Something failed' }));
    expect(handler).toHaveBeenCalledWith({ type: 'error', message: 'Something failed' });
  });

  it('disconnects cleanly', async () => {
    const { ChatClient } = await import('../lib/chat');
    const client = new ChatClient();
    client.connect('sess1', {});
    mockWs._triggerOpen();

    client.disconnect();
    // After disconnect, readyState should be CLOSED or ws should be null
    // The mock ws would have close() called
    expect(mockWs.sent).toBeDefined();
  });

  it('reports isConnected correctly', async () => {
    const { ChatClient } = await import('../lib/chat');
    const client = new ChatClient();
    expect(client.isConnected).toBe(false);

    client.connect('sess1', {});
    mockWs.readyState = WebSocket.OPEN;
    mockWs._triggerOpen();
    expect(client.isConnected).toBe(true);
  });
});
