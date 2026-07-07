// MON NPA Quiz — Service Worker v6
const CACHE = 'mon-npa-v21';

self.addEventListener('install', e => {
  e.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Network-first : toujours la dernière version depuis Netlify
// Fallback sur le cache si pas de connexion
// Ne pas intercepter les Netlify Functions (POST) ni les requêtes Supabase
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = e.request.url;
  if (!url.startsWith(self.location.origin)) return;
  // Ne pas mettre en cache les appels aux fonctions Netlify
  if (url.includes('/.netlify/functions/')) return;

  e.respondWith(
    fetch(e.request)
      .then(resp => {
        if (resp && resp.status === 200) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone)).catch(() => {});
        }
        return resp;
      })
      .catch(() =>
        caches.match(e.request).then(cached =>
          cached || new Response('Offline — please reconnect', { status: 503, statusText: 'Service Unavail