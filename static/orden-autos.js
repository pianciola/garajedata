(() => {
  const btn = document.getElementById("orden-btn"), lista = document.getElementById("lista-autos");
  if (!btn || !lista) return;
  const ayuda = document.getElementById("orden-ayuda");
  let activo = false, guardando = 0;

  function actualizar() {
    const items = [...lista.querySelectorAll(":scope > .car-item")];
    items.forEach((it, i) => {
      const [antes, despues] = it.querySelectorAll("[data-mover]");
      antes.disabled = i === 0;
      despues.disabled = i === items.length - 1;
    });
  }
  function guardar() {
    const ids = [...lista.querySelectorAll(":scope > .car-item")].map((it) => it.dataset.id).join(",");
    fetch(btn.dataset.url, { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/x-www-form-urlencoded",
                 "X-CSRF-Token": document.querySelector("meta[name=csrf]")?.content || "" },
      body: "ids=" + encodeURIComponent(ids) }).catch(() => {});
  }
  btn.addEventListener("click", () => {
    activo = !activo;
    lista.classList.toggle("ordenando", activo);
    btn.textContent = activo ? "✓ Listo" : "⇅ Ordenar";
    ayuda.hidden = !activo;
    lista.querySelectorAll(".orden-ctl").forEach((c) => { c.hidden = !activo; });
    if (activo) actualizar();
  });
  lista.addEventListener("click", (e) => {
    const b = e.target.closest("[data-mover]");
    if (!b) return;
    const it = b.closest(".car-item"), dir = +b.dataset.mover;
    const otro = dir < 0 ? it.previousElementSibling : it.nextElementSibling;
    if (!otro || !otro.matches(".car-item")) return;  // la tarjeta «Agregar vehículo» queda siempre al final
    if (dir < 0) lista.insertBefore(it, otro); else lista.insertBefore(otro, it);
    actualizar();
    guardar();
    it.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
})();
