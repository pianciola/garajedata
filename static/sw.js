// GarajeData: copia local de lo que se ve, para abrir la bitácora y la bóveda
// sin conexión. Siempre intenta la red primero; si no hay, usa la copia.
// Al cerrar sesión la página borra esta copia (ver base.html).
const CACHE = "garajedata-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

function guardable(req, url) {
  if (req.method !== "GET" || url.origin !== self.location.origin) return false;
  if (url.pathname.startsWith("/c/") || url.pathname === "/sw.js") return false;
  // Páginas de autos, archivos de la bóveda y estilos/scripts propios.
  return req.mode === "navigate" || url.pathname.startsWith("/archivo/") || url.pathname.startsWith("/static/");
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (!guardable(e.request, url)) return;
  e.respondWith((async () => {
    try {
      const resp = await fetch(e.request);
      // Solo copias buenas: nada de redirecciones al ingreso ni errores.
      if (resp.ok && !resp.redirected && resp.type === "basic") {
        const copia = resp.clone();
        e.waitUntil(caches.open(CACHE).then((c) => c.put(e.request, copia)));
      }
      return resp;
    } catch (err) {
      const guardada = await caches.match(e.request, { ignoreVary: true });
      if (guardada) return guardada;
      if (e.request.mode === "navigate") {
        return new Response(
          "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>" +
          "<body style='background:#0a0b0d;color:#eef0f3;font-family:system-ui;padding:40px 20px;text-align:center'>" +
          "<h2>Sin conexión</h2><p>Esta página no está guardada en el dispositivo. " +
          "Abrí antes la ficha del auto con conexión para tenerla disponible offline.</p>" +
          "<p><a style='color:#e3262b' href='/'>Volver</a></p>",
          { headers: { "Content-Type": "text/html; charset=utf-8" } });
      }
      throw err;
    }
  })());
});
