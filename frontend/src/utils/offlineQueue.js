/**
 * File d'attente hors-ligne (IndexedDB) pour mutations notes / absences / appel.
 * Sync sur événement online + message SW ; conflits 409/412 → status conflict.
 */

const DB_NAME = 'gs-offline-v2';
const STORE = 'pending';
const DB_VERSION = 1;

function openDb() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB unavailable'));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        const os = db.createObjectStore(STORE, { keyPath: 'id' });
        os.createIndex('status', 'status', { unique: false });
        os.createIndex('createdAt', 'createdAt', { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error || new Error('IDB open failed'));
  });
}

async function idbGetAll() {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const req = tx.objectStore(STORE).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

async function idbPut(item) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(item);
    tx.oncomplete = () => resolve(item);
    tx.onerror = () => reject(tx.error);
  });
}

async function idbDelete(id) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function notifyListeners() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('gs-offline-queue-changed'));
  }
}

/**
 * @param {string} type — notes | absences | appel
 * @param {{ url: string, method?: string, body?: object }} mutation
 * @param {object} [meta]
 */
export async function enqueueOffline(type, mutation, meta = {}) {
  const entry = {
    id: uid(),
    type,
    url: mutation.url || meta.url || '',
    method: (mutation.method || 'POST').toUpperCase(),
    body: mutation.body ?? mutation.payload ?? mutation,
    createdAt: new Date().toISOString(),
    attempts: 0,
    status: 'pending', // pending | conflict | failed
    serverPayload: null,
    meta,
  };
  // rétrocompat : si appelé comme avant (type, payload, meta)
  if (!mutation.url && type === 'notes') {
    const evaluationId = meta.evaluationId || mutation.evaluationId;
    entry.url = `/api/notes/evaluations/${evaluationId}/notes`;
    entry.body = {
      notes: (mutation.notes || mutation).map
        ? (mutation.notes || mutation)
        : mutation.notes || mutation,
    };
    entry.meta = { ...meta, evaluationId };
  } else if (!mutation.url && type === 'absences') {
    entry.url = '/api/absences';
    entry.body = mutation;
  } else if (!mutation.url && type === 'appel') {
    entry.url = '/api/absences/appel';
    entry.body = mutation;
  }

  try {
    await idbPut(entry);
  } catch {
    // Fallback localStorage si IDB indisponible
    const key = 'gs-offline-queue-fallback';
    const raw = localStorage.getItem(key);
    const items = raw ? JSON.parse(raw) : [];
    items.push(entry);
    localStorage.setItem(key, JSON.stringify(items));
  }
  notifyListeners();
  return entry;
}

export async function getOfflineQueue() {
  try {
    return await idbGetAll();
  } catch {
    try {
      const raw = localStorage.getItem('gs-offline-queue-fallback');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }
}

export async function getOfflineQueueCount() {
  const items = await getOfflineQueue();
  return items.filter((i) => i.status !== 'conflict').length;
}

export async function getOfflineConflictCount() {
  const items = await getOfflineQueue();
  return items.filter((i) => i.status === 'conflict').length;
}

export async function clearOfflineQueue() {
  const items = await getOfflineQueue();
  for (const item of items) {
    try {
      await idbDelete(item.id);
    } catch {
      /* ignore */
    }
  }
  localStorage.removeItem('gs-offline-queue-fallback');
  notifyListeners();
}

export async function removeOfflineItem(id) {
  try {
    await idbDelete(id);
  } catch {
    const key = 'gs-offline-queue-fallback';
    const items = (JSON.parse(localStorage.getItem(key) || '[]') || []).filter((i) => i.id !== id);
    localStorage.setItem(key, JSON.stringify(items));
  }
  notifyListeners();
}

async function flushFallbackIntoIdb() {
  const key = 'gs-offline-queue-fallback';
  const raw = localStorage.getItem(key);
  if (!raw) return;
  try {
    const items = JSON.parse(raw);
    for (const item of items) {
      await idbPut(item);
    }
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

/**
 * @returns {Promise<{ synced: number, failed: number, conflicts: number, remaining: number }>}
 */
export async function syncOfflineQueue() {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    const remaining = await getOfflineQueueCount();
    return { synced: 0, failed: 0, conflicts: 0, remaining };
  }

  await flushFallbackIntoIdb();

  const { default: apiClient } = await import('../services/api/client');
  const items = (await getOfflineQueue()).filter((i) => i.status !== 'conflict');
  let synced = 0;
  let failed = 0;
  let conflicts = 0;

  for (const item of items) {
    const next = { ...item, attempts: (item.attempts || 0) + 1 };
    try {
      const url = item.url?.startsWith('/api')
        ? item.url.replace(/^\/api/, '')
        : item.url || '';
      const method = (item.method || 'POST').toLowerCase();
      const res = await apiClient.request({
        url,
        method,
        data: item.body,
        validateStatus: () => true,
      });
      if (res.status === 409 || res.status === 412) {
        next.status = 'conflict';
        next.serverPayload = res.data;
        await idbPut(next);
        conflicts += 1;
        continue;
      }
      if (res.status >= 200 && res.status < 300) {
        await idbDelete(item.id);
        synced += 1;
        continue;
      }
      next.status = 'failed';
      next.serverPayload = res.data;
      await idbPut(next);
      failed += 1;
    } catch (err) {
      next.status = 'failed';
      next.serverPayload = { message: err?.message || 'network' };
      try {
        await idbPut(next);
      } catch {
        /* ignore */
      }
      failed += 1;
    }
  }

  notifyListeners();
  const remaining = await getOfflineQueueCount();
  return { synced, failed, conflicts, remaining };
}

let listenersBound = false;

/** Enregistre sync automatique online + message SW. À appeler depuis main.jsx. */
export function registerOfflineSync() {
  if (typeof window === 'undefined' || listenersBound) return;
  listenersBound = true;

  window.addEventListener('online', () => {
    syncOfflineQueue().catch(() => {});
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'REQUEST_BACKGROUND_SYNC' });
    }
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'SYNC_OFFLINE_QUEUE') {
        syncOfflineQueue().catch(() => {});
      }
    });
  }

  if (navigator.onLine) {
    syncOfflineQueue().catch(() => {});
  }
}
