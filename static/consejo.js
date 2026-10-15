// Dato de garaje del día: «Otro» pide el siguiente y ✕ lo oculta hasta que cambie el del día (se recuerda en el navegador).
(() => {
  const caja = document.getElementById("consejo");
  if (!caja) return;
  const chip = document.getElementById("consejo-abrir");
  const CLAVE = "garaje-consejo-oculto";
  const guardado = () => { try { return localStorage.getItem(CLAVE); } catch { return null; } };
  const guardar = (v) => { try { v ? localStorage.setItem(CLAVE, v) : localStorage.removeItem(CLAVE); } catch { /* sin almacenamiento */ } };
  const ocultar = (si) => { caja.hidden = si; chip.hidden = !si; };
  const quieto = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esperar = (ms) => new Promise((r) => setTimeout(r, quieto ? 0 : ms));
  // Vuelve a disparar una animación aunque la clase ya haya estado puesta.
  const animar = (el, clase, ms) => {
    el.classList.remove(clase);
    void el.offsetWidth;
    el.classList.add(clase);
    setTimeout(() => el.classList.remove(clase), quieto ? 0 : ms);
  };
  // Oculto por el usuario solo mientras sea el mismo consejo del día.
  ocultar(guardado() === caja.dataset.i);

  // Datos ya vistos en este navegador: «Otro» los saltea hasta haberlos visto todos.
  const VISTOS = "garaje-consejos-vistos";
  const vistos = new Set((() => { try { return JSON.parse(localStorage.getItem(VISTOS)) || []; } catch { return []; } })());
  const marcarVisto = (i) => {
    vistos.add(+i);
    try { localStorage.setItem(VISTOS, JSON.stringify([...vistos])); } catch { /* sin almacenamiento */ }
  };
  if (!caja.hidden) marcarVisto(caja.dataset.i);

  // Busca el próximo dato no visto, de a tandas. Si ya se vieron todos, vuelve a empezar.
  const buscarNuevo = async (desde) => {
    for (let vuelta = 0; vuelta < 15; vuelta++) {
      const r = await fetch("/consejos/" + desde, { credentials: "same-origin" });
      if (!r.ok) throw new Error();
      const tanda = await r.json();
      const nuevo = tanda.find((c) => !vistos.has(c.i));
      if (nuevo) return nuevo;
      desde += tanda.length;
    }
    vistos.clear();
    const r = await fetch("/consejos/" + desde, { credentials: "same-origin" });
    return (await r.json())[0];
  };

  document.getElementById("consejo-cerrar").addEventListener("click", async () => {
    guardar(caja.dataset.i);
    caja.classList.add("consejo-cerrando");
    await esperar(420);
    caja.classList.remove("consejo-cerrando");
    ocultar(true);
    animar(chip, "consejo-entra", 400);
  });
  chip.addEventListener("click", () => {
    guardar(null);
    ocultar(false);
    marcarVisto(caja.dataset.i);
    animar(caja, "consejo-abriendo", 700);
  });

  const otro = document.getElementById("consejo-otro");
  otro.addEventListener("click", async () => {
    const salto = (+caja.dataset.salto || 0) + 1;
    otro.disabled = true;
    caja.classList.remove("consejo-entra");
    caja.classList.add("consejo-sale");
    try {
      const [c] = await Promise.all([buscarNuevo(salto), esperar(180)]);
      caja.dataset.salto = c.salto;
      marcarVisto(c.i);
      caja.className = "consejo consejo-" + c.clave;
      document.getElementById("consejo-cat").textContent = c.categoria;
      document.getElementById("consejo-num").textContent = "#" + String(c.i + 1).padStart(2, "0");
      document.getElementById("consejo-texto").textContent = c.texto;
    } catch { /* sin conexión: queda el dato actual */ } finally {
      caja.classList.remove("consejo-sale");
      animar(caja, "consejo-entra", 600);
      otro.disabled = false;
    }
  });
})();
