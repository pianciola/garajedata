// Cartel lateral de recordatorios: entra deslizándose desde el costado, no tapa
// el centro y se va solo. Cada aviso se muestra una vez por sesión del navegador;
// "Recordármelo mañana" lo silencia 24 horas.
(() => {
  const cartel = document.getElementById("cartel");
  if (!cartel) return;
  const LS = "garaje-avisos-silenciados", SS = "garaje-avisos-vistos";
  const leer = (almacen, clave, defecto) => {
    try { return JSON.parse(almacen.getItem(clave)) ?? defecto; } catch { return defecto; }
  };
  const escribir = (almacen, clave, valor) => {
    try { almacen.setItem(clave, JSON.stringify(valor)); } catch { /* sin almacenamiento */ }
  };

  const ahora = Date.now();
  const silenciados = leer(localStorage, LS, {});
  const vistos = leer(sessionStorage, SS, []);
  for (const li of cartel.querySelectorAll("li[data-clave]")) {
    if ((silenciados[li.dataset.clave] || 0) > ahora || vistos.includes(li.dataset.clave)) li.remove();
  }
  const pendientes = [...cartel.querySelectorAll("li[data-clave]")];
  if (!pendientes.length) { cartel.remove(); return; }
  cartel.classList.toggle("cartel-urgente", pendientes.some((li) => li.classList.contains("cartel-vencido")));

  let temporizador;
  const cerrar = () => { clearTimeout(temporizador); cartel.classList.remove("abierto"); };
  const programar = () => { clearTimeout(temporizador); temporizador = setTimeout(cerrar, 14000); };

  setTimeout(() => {
    cartel.classList.add("abierto");
    escribir(sessionStorage, SS, [...vistos, ...pendientes.map((li) => li.dataset.clave)]);
    programar();
  }, 1400);

  cartel.addEventListener("mouseenter", () => clearTimeout(temporizador));
  cartel.addEventListener("mouseleave", programar);
  cartel.addEventListener("focusin", () => clearTimeout(temporizador));
  cartel.querySelector("[data-cerrar]").addEventListener("click", cerrar);
  cartel.querySelector("[data-manana]").addEventListener("click", () => {
    const hasta = Date.now() + 24 * 3600 * 1000;
    for (const li of pendientes) silenciados[li.dataset.clave] = hasta;
    escribir(localStorage, LS, silenciados);
    cerrar();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrar(); });
})();
