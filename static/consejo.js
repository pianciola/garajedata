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
    animar(caja, "consejo-abriendo", 700);
  });

  const otro = document.getElementById("consejo-otro");
  otro.addEventListener("click", async () => {
    const salto = (+caja.dataset.salto || 0) + 1;
    otro.disabled = true;
    caja.classList.remove("consejo-entra");
    caja.classList.add("consejo-sale");
    try {
      const [r] = await Promise.all([fetch("/consejo/" + salto, { credentials: "same-origin" }), esperar(180)]);
      if (!r.ok) throw new Error();
      const c = await r.json();
      caja.dataset.salto = salto;
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
