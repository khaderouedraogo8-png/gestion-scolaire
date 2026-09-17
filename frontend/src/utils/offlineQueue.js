/**
 * File d'attente hors-ligne pour notes et absences.
 * Persistance localStorage + sync quand le réseau revient.
 */

const STORAGE_KEY = 'gs-offline-queue-v1';

function readQueue() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeQueue(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * @param {'notes'|'absences'} type
 * @param {object} payload — payload API prêt à envoyer
 * @param {{ evaluationId?: string }} [meta]
 */
export function enqueueOffline(type, payload, meta = {}) {
  const items = readQueue();
  const entry = {
    id: uid(),
    type,
    payload,
    meta,
    createdAt: new Date().toISOString(),
    attempts: 0,
  };
  items.push(entry);
  writeQueue(items);
  return entry;
}

export function getOfflineQueue() {
  return readQueue();
}

export function getOfflineQueueCount() {
  return readQueue().length;
}

export function clearOfflineQueue() {
  writeQueue([]);
}

export function removeOfflineItem(id) {
  writeQueue(readQueue().filter((i) => i.id !== id));
}

/**
 * Synchronise la file via les clients API (imports dynamiques pour éviter cycles).
 * @returns {{ synced: number, failed: number, remaining: number }}
 */
export async function syncOfflineQueue() {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return { synced: 0, failed: 0, remaining: getOfflineQueueCount() };
  }

  const { notesApi } = await import('../services/api/notes');
  const { absencesApi } = await import('../services/api/absences');

  const items = readQueue();
  const remaining = [];
  let synced = 0;
  let failed = 0;

  for (const item of items) {
    try {
      if (item.type === 'notes') {
        const evaluationId = item.meta?.evaluationId || item.payload?.evaluationId;
        const notes = item.payload?.notes || item.payload;
        await notesApi.saveNotes(evaluationId, notes);
      } else if (item.type === 'absences') {
        await absencesApi.create(item.payload);
      } else {
        remaining.push(item);
        continue;
      }
      synced += 1;
    } catch {
      failed += 1;
      remaining.push({ ...item, attempts: (item.attempts || 0) + 1 });
    }
  }

  writeQueue(remaining);
  return { synced, failed, remaining: remaining.length };
}

let listenersBound = false;

/** Enregistre sync automatique online + message SW. À appeler depuis main.jsx. */
export function registerOfflineSync() {
  if (typeof window === 'undefined' || listenersBound) return;
  listenersBound = true;

  window.addEventListener('online', () => {
    syncOfflineQueue().catch(() => {});
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
