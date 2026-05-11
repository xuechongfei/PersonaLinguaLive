export interface VocabEntry {
  word: string;
  definition: string;
  example: string;
}

export interface ConversationSummary {
  newWords: VocabEntry[];
  grammarPoints: string[];
  fluencyScore: number;
  strengths: string[];
  areasToImprove: string[];
}

export interface ConversationData {
  sessionId: string;
  personaId: string;
  personaName: string;
  turns: Array<{
    userMessage: string;
    assistantResponse: { speak: string; learning: string; followup: string };
    timestamp: number;
  }>;
  createdAt: number;
  updatedAt: number;
  summary?: ConversationSummary;
}

export interface VocabRecord {
  word: string;
  definition: string;
  example: string;
  sessionId: string;
  addedAt: number;
  dueAt: number;
  ease: number;
  intervalDays: number;
  reps: number;
}

const DB_NAME = 'PersonaLinguaLiveDB';
const DB_VERSION = 2;

function _openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains('images')) {
        db.createObjectStore('images');
      }
      if (!db.objectStoreNames.contains('conversations')) {
        db.createObjectStore('conversations', { keyPath: 'sessionId' });
      }
      if (!db.objectStoreNames.contains('preferences')) {
        db.createObjectStore('preferences');
      }
      if (!db.objectStoreNames.contains('vocabulary')) {
        db.createObjectStore('vocabulary', { keyPath: 'word' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Images
export async function saveImage(key: string, blob: Blob): Promise<void> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('images', 'readwrite');
    tx.objectStore('images').put(blob, key);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

export async function getImage(key: string): Promise<Blob | undefined> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('images', 'readonly');
    const req = tx.objectStore('images').get(key);
    req.onsuccess = () => { db.close(); resolve(req.result ?? undefined); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

export async function getAllImageKeys(): Promise<string[]> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('images', 'readonly');
    const req = tx.objectStore('images').getAllKeys();
    req.onsuccess = () => { db.close(); resolve(req.result as string[]); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

// Conversations
export async function saveConversation(_sessionId: string, data: ConversationData): Promise<void> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('conversations', 'readwrite');
    tx.objectStore('conversations').put(data);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

export async function getConversation(sessionId: string): Promise<ConversationData | undefined> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('conversations', 'readonly');
    const req = tx.objectStore('conversations').get(sessionId);
    req.onsuccess = () => { db.close(); resolve(req.result ?? undefined); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

export async function getAllConversationIds(): Promise<string[]> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('conversations', 'readonly');
    const req = tx.objectStore('conversations').getAllKeys();
    req.onsuccess = () => { db.close(); resolve(req.result as string[]); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

// Preferences
export async function savePreference(key: string, value: unknown): Promise<void> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('preferences', 'readwrite');
    tx.objectStore('preferences').put(value, key);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

export async function getPreference(key: string): Promise<unknown | undefined> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('preferences', 'readonly');
    const req = tx.objectStore('preferences').get(key);
    req.onsuccess = () => { db.close(); resolve(req.result ?? undefined); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

// Clear
export async function clearStore(storeName: string): Promise<void> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).clear();
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

export async function clearAll(): Promise<void> {
  await Promise.all([
    clearStore('images'),
    clearStore('conversations'),
    clearStore('preferences'),
    clearStore('vocabulary'),
  ]);
}

// Vocabulary
export async function saveWord(entry: VocabRecord): Promise<void> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('vocabulary', 'readwrite');
    const store = tx.objectStore('vocabulary');
    // Preserve SRS state when the word already exists
    const getReq = store.get(entry.word);
    getReq.onsuccess = () => {
      const existing = getReq.result as VocabRecord | undefined;
      const merged: VocabRecord = existing
        ? {
            ...existing,
            // Only refresh definition/example when the new entry has content
            definition: entry.definition || existing.definition,
            example: entry.example || existing.example,
          }
        : entry;
      store.put(merged);
    };
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

export async function getWord(word: string): Promise<VocabRecord | undefined> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('vocabulary', 'readonly');
    const req = tx.objectStore('vocabulary').get(word);
    req.onsuccess = () => { db.close(); resolve(req.result ?? undefined); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

export async function getAllWords(): Promise<VocabRecord[]> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('vocabulary', 'readonly');
    const req = tx.objectStore('vocabulary').getAll();
    req.onsuccess = () => { db.close(); resolve((req.result as VocabRecord[]) ?? []); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

export async function getDueWords(now: number = Date.now()): Promise<VocabRecord[]> {
  const all = await getAllWords();
  return all.filter((w) => w.dueAt <= now);
}

export async function updateWordSchedule(
  word: string,
  updates: Pick<VocabRecord, 'ease' | 'intervalDays' | 'dueAt' | 'reps'>,
): Promise<void> {
  const db = await _openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('vocabulary', 'readwrite');
    const store = tx.objectStore('vocabulary');
    const getReq = store.get(word);
    getReq.onsuccess = () => {
      const existing = getReq.result as VocabRecord | undefined;
      if (existing) {
        store.put({ ...existing, ...updates });
      }
    };
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}
