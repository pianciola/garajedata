// Botón flotante «+ Nuevo registro» del celular: aparece solo cuando el botón principal de la página
// ya no está a la vista (así nunca hay dos iguales en pantalla). Si la página no tiene botón principal, se ve siempre.
(() => {
  const flotante = document.querySelector(".carga-flotante");
  if (!flotante) return;
  const principal = document.querySelector("[data-registro-principal]");
  if (!principal) {
    flotante.classList.remove("carga-oculta");
    return;
  }
  const barra = document.querySelector(".topbar");
  const revisar = () => {
    const r = principal.getBoundingClientRect();
    const arriba = barra ? barra.getBoundingClientRect().bottom : 0;
    // Visible = al menos la mitad del botón entre la barra de arriba y el borde de abajo de la pantalla.
    const visible = r.bottom - r.height / 2 > arriba && r.top + r.height / 2 < window.innerHeight;
    flotante.classList.toggle("carga-oculta", visible);
  };
  // Es una sola medición: barata aunque se haga en cada movimiento del scroll.
  window.addEventListener("scroll", revisar, { passive: true });
  window.addEventListener("resize", revisar);
  revisar();
})();
