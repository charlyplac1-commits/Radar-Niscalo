/* Radar Níscalo — Service Worker sin caché de la interfaz. */
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

  event.respondWith((async()=>{
    try{
      const response=await fetch(event.request,{cache:"no-store"});
      const tipo=response.headers.get("content-type")||"";
      if(event.request.mode==="navigate" || tipo.includes("text/html")){
        const html=await response.text();
        if(html.includes("</body>") && !html.includes("route-gps-fix.js")){
          const mod=html.replace("</body>",'<script src="route-gps-fix.js?v=1"></script></body>');
          return new Response(mod,{status:response.status,statusText:response.statusText,headers:response.headers});
        }
      }
      return response;
    }catch(e){
      return caches.match(event.request);
    }
  })());
});