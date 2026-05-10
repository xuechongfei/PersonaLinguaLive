import { describe, it, expect, beforeEach, vi } from 'vitest';

// ---------------------------------------------------------------------------
// In-memory store backing the mock IndexedDB, scoped by store name
// ---------------------------------------------------------------------------
const mockStore = new Map<string, Map<string, any>>();

// ---------------------------------------------------------------------------
// Mock IndexedDB — each call to transaction() creates a fresh transaction with
// its own oncomplete/onerror, scoped to the named object store.
// ---------------------------------------------------------------------------
const mockDb = {
  transaction: vi.fn((storeName: string) => {
    // Ensure the named store exists in the mock
    if (!mockStore.has(storeName)) mockStore.set(storeName, new Map());
    const storeMap = mockStore.get(storeName)!;

    const tx: {
      objectStore: ReturnType<typeof vi.fn>;
      oncomplete: (() => void) | null;
      onerror: (() => void) | null;
    } = {
      objectStore: null as unknown as ReturnType<typeof vi.fn>,
      oncomplete: null,
      onerror: null,
    };
    tx.objectStore = vi.fn(() => ({
      put: vi.fn((value: any, key?: string) => {
        const actualKey = key ?? (value as any).sessionId;
        storeMap.set(actualKey, value);
        setTimeout(() => tx.oncomplete?.(), 0);
      }),
      get: vi.fn((key: string) => {
        const req = { result: storeMap.get(key), onsuccess: null as any };
        setTimeout(() => req.onsuccess?.(), 0);
        return req;
      }),
      getAllKeys: vi.fn(() => {
        const req = { result: [...storeMap.keys()], onsuccess: null as any };
        setTimeout(() => req.onsuccess?.(), 0);
        return req;
      }),
      clear: vi.fn(() => {
        storeMap.clear();
        setTimeout(() => tx.oncomplete?.(), 0);
      }),
    }));
    return tx;
  }),
  close: vi.fn(),
  objectStoreNames: {
    contains: vi.fn(() => true),
  },
};

// ---------------------------------------------------------------------------
// Global mock setup — runs before any test in this file
// ---------------------------------------------------------------------------
vi.stubGlobal('indexedDB', {
  open: vi.fn(() => {
    const request = {
      result: mockDb,
      onupgradeneeded: null as any,
      onsuccess: null as any,
      onerror: null as any,
    };
    setTimeout(() => request.onsuccess?.(null as any), 0);
    return request;
  }),
});

beforeEach(() => {
  mockStore.clear();
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('storage — images', () => {
  it('saveImage stores a blob and getImage retrieves it', async () => {
    const { saveImage, getImage } = await import('../lib/storage');
    const blob = new Blob(['test image data'], { type: 'image/png' });

    await saveImage('key1', blob);
    const retrieved = await getImage('key1');

    expect(retrieved).toBeInstanceOf(Blob);
    expect((retrieved as Blob).size).toBeGreaterThan(0);
    expect(mockDb.transaction).toHaveBeenCalledWith('images', 'readwrite');
  });

  it('getImage returns undefined for a missing key', async () => {
    const { getImage } = await import('../lib/storage');
    const result = await getImage('nonexistent');
    expect(result).toBeUndefined();
  });

  it('getAllImageKeys returns all stored keys', async () => {
    const { saveImage, getAllImageKeys } = await import('../lib/storage');
    await saveImage('a', new Blob(['a']));
    await saveImage('b', new Blob(['b']));
    await saveImage('c', new Blob(['c']));

    const keys = await getAllImageKeys();
    expect(keys).toEqual(['a', 'b', 'c']);
  });

  it('getAllImageKeys returns an empty array when no images exist', async () => {
    const { getAllImageKeys } = await import('../lib/storage');
    const keys = await getAllImageKeys();
    expect(keys).toEqual([]);
  });
});

describe('storage — conversations', () => {
  const sampleConversation = {
    sessionId: 'sess-001',
    personaId: 'p1',
    personaName: 'Tilly',
    turns: [
      {
        userMessage: 'Hello',
        assistantResponse: {
          speak: 'Hi there!',
          learning: 'Greeting',
          followup: 'How are you?',
        },
        timestamp: 1000,
      },
    ],
    createdAt: 1000,
    updatedAt: 1000,
  };

  it('saveConversation stores data and getConversation retrieves it', async () => {
    const { saveConversation, getConversation } = await import('../lib/storage');
    await saveConversation('sess-001', sampleConversation);
    const retrieved = await getConversation('sess-001');
    expect(retrieved).toEqual(sampleConversation);
  });

  it('getConversation returns undefined for a missing session', async () => {
    const { getConversation } = await import('../lib/storage');
    const result = await getConversation('nonexistent');
    expect(result).toBeUndefined();
  });

  it('saveConversation overwrites an existing conversation', async () => {
    const { saveConversation, getConversation } = await import('../lib/storage');
    await saveConversation('sess-001', sampleConversation);

    const updated = { ...sampleConversation, updatedAt: 2000 };
    await saveConversation('sess-001', updated);
    const retrieved = await getConversation('sess-001');
    expect(retrieved!.updatedAt).toBe(2000);
  });

  it('getAllConversationIds returns all stored session IDs', async () => {
    const { saveConversation, getAllConversationIds } = await import('../lib/storage');
    await saveConversation('sess-a', { ...sampleConversation, sessionId: 'sess-a' });
    await saveConversation('sess-b', { ...sampleConversation, sessionId: 'sess-b' });

    const ids = await getAllConversationIds();
    expect(ids).toEqual(['sess-a', 'sess-b']);
  });
});

describe('storage — preferences', () => {
  it('savePreference stores a value and getPreference retrieves it', async () => {
    const { savePreference, getPreference } = await import('../lib/storage');
    await savePreference('theme', 'dark');
    const value = await getPreference('theme');
    expect(value).toBe('dark');
  });

  it('savePreference stores complex (object) values', async () => {
    const { savePreference, getPreference } = await import('../lib/storage');
    const prefs = { language: 'zh-CN', level: 'beginner' };
    await savePreference('user_settings', prefs);
    const retrieved = await getPreference('user_settings');
    expect(retrieved).toEqual(prefs);
  });

  it('getPreference returns undefined for a missing key', async () => {
    const { getPreference } = await import('../lib/storage');
    const result = await getPreference('nonexistent');
    expect(result).toBeUndefined();
  });
});

describe('storage — clear', () => {
  it('clearAll empties every store', async () => {
    const {
      saveImage,
      saveConversation,
      savePreference,
      clearAll,
      getAllImageKeys,
      getAllConversationIds,
      getPreference,
    } = await import('../lib/storage');

    const convData = {
      sessionId: 's1',
      personaId: 'p1',
      personaName: 'Tilly',
      turns: [],
      createdAt: 1,
      updatedAt: 1,
    };

    await saveImage('img1', new Blob(['img']));
    await saveConversation('s1', convData);
    await savePreference('theme', 'dark');

    await clearAll();

    expect(await getAllImageKeys()).toEqual([]);
    expect(await getPreference('theme')).toBeUndefined();
    expect(await getAllConversationIds()).toEqual([]);
  });

  it('clearStore clears only the specified store', async () => {
    const { saveImage, savePreference, clearStore, getImage, getPreference } =
      await import('../lib/storage');

    await saveImage('img1', new Blob(['img']));
    await savePreference('theme', 'dark');

    await clearStore('images');

    expect(await getImage('img1')).toBeUndefined();
    expect(await getPreference('theme')).toBe('dark');
  });
});
