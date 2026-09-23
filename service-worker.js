/* Radar Níscalo — Service Worker sin caché de la interfaz.
   La aplicación es estática y debe cargar siempre la versión publicada de GitHub Pages. */
const CACHE_NAME="radar-niscalo-disabled-v1";

self.addEventListener("install",event=>{
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate",event=>{
  event.waitUntil((async()=>{
    const keys=await caches.keys();
    await Promise.all(keys.map(key=>caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET") return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin) return;

  event.respondWith(
    fetch(event.request,{cache:"no-store"}).catch(()=>caches.match(event.request))
  );
});