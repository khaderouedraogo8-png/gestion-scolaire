const CACHE = 'gestion-scolaire-v4';
const ASSETS = ['/', '/index.html', '/manifest.json', '/favicon.svg', '/login'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.pathname.startsWith('/api')) {
    if (request.method === 'GET') {
      event.respondWith(
        fetch(request)
          .then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE).then((cache) => cache.put(request, clone));
            }
            return response;
          })
          .catch(() => caches.match(request))
      );
    }
    return;
  }

  if (request.method !== 'GET') return;

  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((response) => {
          if (response.ok && url.origin === self.location.origin) {
            const clone = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => cached);
      return cached || fetchPromise;
    })
  );
});

function broadcastSync() {
  return self.clients.matchAll({ type: 'window' }).then((clients) => {
    clients.forEach((client) => client.postMessage({ type: 'SYNC_OFFLINE_QUEUE' }));
  });
}

self.addEventListener('sync', (event) => {
  if (event.tag === 'gs-offline-sync') {
    event.waitUntil(broadcastSync());
  }
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (event.data?.type === 'REQUEST_BACKGROUND_SYNC') {
    event.waitUntil(
      (async () => {
        try {
          if (self.registration && 'sync' in self.registration) {
            await self.registration.sync.register('gs-offline-sync');
          }
        } catch {
          /* Background Sync may be unavailable */
        }
        await broadcastSync();
      })()
    );
  }
  if (event.data?.type === 'SYNC_OFFLINE_QUEUE') {
    event.waitUntil(broadcastSync());
  }
});

self.addEventListener('online', () => {
  broadcastSync();
});
