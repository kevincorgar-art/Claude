const V='v11';
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(V).then(c=>Promise.all(['./','index.html','manifest.webmanifest','icon-192.png','https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js','https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js'].map(u=>c.add(u).catch(()=>{}))))});
self.addEventListener('activate',e=>e.waitUntil(clients.claim()));
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);
  if(e.request.method!=='GET'||!(u.origin===location.origin||u.hostname==='cdnjs.cloudflare.com'||u.hostname==='cdn.jsdelivr.net'))return;
  e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(V).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request)))});
