// El acceso móvil acompaña el scroll sin duplicar el botón que ya está a la vista.
(() => {
  const flotante = document.querySelector('.carga-flotante');
  const principal = document.querySelector('main a[href^="/cargar"]');
  if (!flotante || !principal || !('IntersectionObserver' in window)) return;
  new IntersectionObserver(([entry]) => {
    flotante.classList.toggle('carga-oculta', entry.isIntersecting);
  }, { threshold: .15 }).observe(principal);
})();
