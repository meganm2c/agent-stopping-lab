// Static files only. Bump the version when publishing updated replay assets.
const CACHE = 'agent-stopping-cross-harness-v1';
const ASSETS = [
 './', 'index.html', 'static/app.js', 'static/archive.js', 'static/openclaw.js',
 'static/openclaw.json', 'static/style.css', 'data/scenarios.json',
 'results/phoenix-20260928T011340Z/runs.jsonl',
 'results/phoenix-20260928T011340Z/comparison.json',
 'results/phase3-comparison/runs.jsonl', 'results/phase3-comparison/summary.json',
 'results/phase3-comparison/demo-traces.json', 'results/phase3-variation/summary.json',
 'results/phase3-variation/runs.jsonl', 'results/screenshots/adaptive-comparison-metrics.png',
 'static/screenshots/budget-evals.png', 'static/screenshots/evidence-evals.png',
 'static/screenshots/repeat-a.png', 'static/screenshots/repeat-b.png', 'static/screenshots/adaptive-stop.png',
 'OPENCLAW_RESULTS.md', 'OPENCLAW_COMPARISON.md', 'spikes/openclaw-followup/TESTING.md'
];
const urls = new Set(ASSETS.map(p => new URL(p, self.registration.scope).href));
self.addEventListener('install', event => event.waitUntil(
 caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting())
));
self.addEventListener('activate', event => event.waitUntil(
 caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('agent-stopping-cross-harness-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())
));
self.addEventListener('fetch', event => {
 if (event.request.method !== 'GET' || !urls.has(event.request.url)) return;
 event.respondWith(caches.open(CACHE).then(async cache => (await cache.match(event.request)) || fetch(event.request)));
});
