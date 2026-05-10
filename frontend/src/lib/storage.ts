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
}

const DB_NAME = 'PersonaLinguaLiveDB';
const DB_VERSION = 1;

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
export async function saveConversation(sessionId: string, data: ConversationData): Promise<void> {
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
  ]);
}
