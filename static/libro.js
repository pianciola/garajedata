// Libro de servicio: elegir qué se ve en el PDF y qué no.
// Las casillas "data-toggle" ocultan las secciones marcadas con data-s; cada
// registro tiene su casilla "Incluir". El resumen (cantidad, período, total y
// etiquetas) se recalcula con lo que queda visible. Las elecciones se guardan
// en este dispositivo.
(() => {
  const libro = document.getElementById("libro");
  if (!libro) return;
  const clave = libro.dataset.clave;
  const items = [...libro.querySelectorAll(".libro-item")];
  const toggles = [...document.querySelectorAll("[data-toggle]")];

  // Estado: secciones apagadas y registros excluidos.
  let estado = { apagadas: [], excluidos: [] };
  try { estado = { ...estado, ...JSON.parse(localStorage.getItem(clave) || "{}") }; } catch { /* sin almacenamiento */ }
  const guardar = () => { try { localStorage.setItem(clave, JSON.stringify(estado)); } catch { /* sin almacenamiento */ } };

  // Sin la sección en la página (ej. costos ocultos por el dueño) no se ofrece la casilla.
  for (const t of toggles) {
    if (!libro.querySelector(`[data-s="${t.dataset.toggle}"]`)) t.closest("label").hidden = true;
    else t.checked = !estado.apagadas.includes(t.dataset.toggle);
  }
  for (const it of items) {
    it.querySelector("[data-incluir]").checked = !estado.excluidos.includes(it.dataset.id);
  }

  const fecha = (iso) => iso.split("-").reverse().join("/");
  const plata = (n) => "$ " + n.toLocaleString("es-AR", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });

  function aplicar() {
    for (const t of toggles) {
      libro.querySelectorAll(`[data-s="${t.dataset.toggle}"]`).forEach((el) => { el.hidden = !t.checked; });
    }
    // Un item solo muestra "Fecha + km" si alguno de los dos se ve; no hay nada más que ocultar.
    const visibles = items.filter((it) => it.querySelector("[data-incluir]").checked);
    items.forEach((it) => { it.classList.toggle("excluido", !visibles.includes(it)); });

    // Resumen recalculado con los registros incluidos.
    const n = document.getElementById("res-n");
    if (n) n.textContent = visibles.length;
    const per = document.getElementById("res-periodo");
    if (per) {
      const fechas = visibles.map((it) => it.dataset.fecha).sort();
      per.textContent = fechas.length ? `${fecha(fechas[0])} – ${fecha(fechas[fechas.length - 1])}` : "—";
    }
    const tot = document.getElementById("res-total");
    if (tot) tot.textContent = plata(visibles.reduce((s, it) => s + (parseFloat(it.dataset.costo) || 0), 0));
    document.querySelectorAll("#libro-cats [data-cat]").forEach((c) => {
      const cant = visibles.filter((it) => it.dataset.cat === c.dataset.cat).length;
      c.textContent = `${c.dataset.etiqueta}: ${cant}`;
      c.hidden = !cant;
    });
    const pie = document.getElementById("libro-pie");
    if (pie) {
      const fechas = visibles.map((it) => it.dataset.fecha).sort();
      pie.textContent = "Historial cargado por el dueño del vehículo en GarajeData." +
        (fechas.length ? ` ${visibles.length} ${visibles.length === 1 ? "registro" : "registros"} entre el ${fecha(fechas[0])} y el ${fecha(fechas[fechas.length - 1])}.` : "");
    }
    // Una fila de resumen sin celdas visibles no deja huecos.
    const res = document.getElementById("resumen");
    if (res) res.hidden = [...res.children].every((c) => c.hidden);
    const cats = document.getElementById("libro-cats");
    if (cats) cats.hidden = cats.hidden || [...cats.children].every((c) => c.hidden);

    estado.apagadas = toggles.filter((t) => !t.checked).map((t) => t.dataset.toggle);
    estado.excluidos = items.filter((it) => !it.querySelector("[data-incluir]").checked).map((it) => it.dataset.id);
    guardar();
  }

  toggles.forEach((t) => t.addEventListener("change", aplicar));
  items.forEach((it) => it.querySelector("[data-incluir]").addEventListener("change", aplicar));
  document.querySelectorAll("[data-todo]").forEach((b) => b.addEventListener("click", () => {
    toggles.forEach((t) => { t.checked = b.dataset.todo === "1"; });
    aplicar();
  }));
  document.querySelectorAll("[data-registros]").forEach((b) => b.addEventListener("click", () => {
    items.forEach((it) => { it.querySelector("[data-incluir]").checked = b.dataset.registros === "1"; });
    aplicar();
  }));
  aplicar();
})();
