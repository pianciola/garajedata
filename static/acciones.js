// Acciones que antes eran atributos en línea (onsubmit/onclick): con la política de seguridad del sitio
// no se permiten, así que se declaran con data-* y se resuelven acá.
document.addEventListener("submit", (e) => {
  const mensaje = e.target.dataset && e.target.dataset.confirmar;
  if (mensaje && !confirm(mensaje)) e.preventDefault();
});
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-imprimir]")) window.print();
});
// Formularios que se envían solos al cambiar un desplegable (por ejemplo, el mes del calendario).
document.addEventListener("change", (e) => {
  const form = e.target.closest("form[data-autoenviar]");
  if (form && (e.target.matches("select") || (e.target.type === "file" && e.target.files.length))) form.submit();
});
document.querySelectorAll("form[data-autoenviar] [data-sin-js]").forEach((b) => { b.hidden = true; });

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

// Pestañas de «Mi cuenta» (sin JavaScript se ven todas las secciones una debajo de otra).
(() => {
  const tabs = [...document.querySelectorAll("[data-tab]")];
  if (!tabs.length) return;
  const paneles = [...document.querySelectorAll("[data-panel]")];
  document.querySelector(".cuenta").classList.add("con-tabs");
  function mostrar(nombre, guardar) {
    if (!paneles.some((p) => p.dataset.panel === nombre)) nombre = "seguridad";
    tabs.forEach((t) => { const on = t.dataset.tab === nombre; t.classList.toggle("activa", on); t.setAttribute("aria-selected", on); });
    paneles.forEach((p) => { p.hidden = p.dataset.panel !== nombre; });
    if (guardar) history.replaceState(null, "", "#" + nombre);
  }
  tabs.forEach((t) => t.addEventListener("click", () => mostrar(t.dataset.tab, true)));
  mostrar(location.hash.slice(1) || "seguridad", false);
})();

// Botón «Ver» en los campos de contraseña.
document.querySelectorAll('input[type="password"]').forEach((campo) => {
  const envoltorio = document.createElement("div");
  envoltorio.className = "clave-wrap";
  campo.parentNode.insertBefore(envoltorio, campo);
  envoltorio.appendChild(campo);
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "clave-ver";
  boton.textContent = "Ver";
  boton.setAttribute("aria-label", "Mostrar la contraseña");
  boton.addEventListener("click", () => {
    const ver = campo.type === "password";
    campo.type = ver ? "text" : "password";
    boton.textContent = ver ? "Ocultar" : "Ver";
    boton.setAttribute("aria-label", ver ? "Ocultar la contraseña" : "Mostrar la contraseña");
    campo.focus();
  });
  envoltorio.appendChild(boton);
});

// Menú «⋯» de cada vehículo: se cierra al tocar afuera o con Escape (y solo uno abierto a la vez).
document.addEventListener("click", (e) => {
  document.querySelectorAll("details.car-menu[open]").forEach((d) => { if (!d.contains(e.target)) d.open = false; });
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") document.querySelectorAll("details.car-menu[open]").forEach((d) => { d.open = false; });
});
