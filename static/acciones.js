// Acciones que antes eran atributos en línea (onsubmit/onclick): con la política de seguridad del sitio
// no se permiten, así que se declaran con data-* y se resuelven acá.
document.addEventListener("submit", (e) => {
  const mensaje = e.target.dataset && e.target.dataset.confirmar;
  if (mensaje && !confirm(mensaje)) e.preventDefault();
});
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-imprimir]")) window.print();
});

// Campos de fecha opcionales: botón para borrarlos (el selector del navegador no siempre deja vaciarlos).
document.querySelectorAll('input[type="date"]:not([required])').forEach((campo) => {
  const envoltorio = document.createElement("div");
  envoltorio.className = "fecha-wrap";
  campo.parentNode.insertBefore(envoltorio, campo);
  envoltorio.appendChild(campo);
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "fecha-borrar";
  boton.textContent = "Borrar fecha";
  boton.addEventListener("click", () => { campo.value = ""; campo.dispatchEvent(new Event("input", { bubbles: true })); mostrar(); campo.focus(); });
  envoltorio.appendChild(boton);
  const mostrar = () => { boton.hidden = !campo.value; };
  campo.addEventListener("input", mostrar);
  campo.addEventListener("change", mostrar);
  mostrar();
});
