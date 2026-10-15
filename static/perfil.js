// Cada entrada, incluida la restauración desde la caché de Atrás.
(() => {
  const perfil = document.querySelector('[data-perfil-auto]');
  if (!perfil) return;
  const movimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
  let cierre;
  function terminar() {
    clearTimeout(cierre);
    perfil.classList.remove('perfil-entrando');
  }
  function entrar() {
    terminar();
    if (movimiento.matches || document.hidden) return;
    void perfil.offsetWidth;
    perfil.classList.add('perfil-entrando');
    cierre = setTimeout(terminar, 1150);
  }
  entrar();
  window.addEventListener('pageshow', (evento) => { if (evento.persisted) entrar(); });
  window.addEventListener('pagehide', terminar);
  movimiento.addEventListener('change', terminar);
  perfil.addEventListener('pointerdown', terminar, { passive: true });
  perfil.addEventListener('focusin', terminar);
})();
