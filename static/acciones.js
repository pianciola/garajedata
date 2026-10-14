// Acciones que antes eran atributos en línea (onsubmit/onclick): con la política de seguridad del sitio
// no se permiten, así que se declaran con data-* y se resuelven acá.
document.addEventListener("submit", (e) => {
  const mensaje = e.target.dataset && e.target.dataset.confirmar;
  if (mensaje && !confirm(mensaje)) e.preventDefault();
});
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-imprimir]")) window.print();
});
