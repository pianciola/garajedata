// Consejo del día: «Otro» pide el siguiente y ✕ lo oculta hasta que cambie el del día (se recuerda en el navegador).
(() => {
  const caja = document.getElementById("consejo");
  if (!caja) return;
  const chip = document.getElementById("consejo-abrir");
  const CLAVE = "garaje-consejo-oculto";
  const guardado = () => { try { return localStorage.getItem(CLAVE); } catch { return null; } };
  const guardar = (v) => { try { v ? localStorage.setItem(CLAVE, v) : localStorage.removeItem(CLAVE); } catch { /* sin almacenamiento */ } };
  const ocultar = (si) => { caja.hidden = si; chip.hidden = !si; };
  // Oculto por el usuario solo mientras sea el mismo consejo del día.
  ocultar(guardado() === caja.dataset.i);

  document.getElementById("consejo-cerrar").addEventListener("click", () => { guardar(caja.dataset.i); ocultar(true); });
  chip.addEventListener("click", () => { guardar(null); ocultar(false); });

  const otro = document.getElementById("consejo-otro");
  otro.addEventListener("click", async () => {
    const salto = (+caja.dataset.salto || 0) + 1;
    otro.disabled = true;
    try {
      const r = await fetch("/consejo/" + salto, { credentials: "same-origin" });
      if (!r.ok) return;
      const c = await r.json();
      caja.dataset.salto = salto;
      caja.className = "consejo consejo-" + c.clave;
      document.getElementById("consejo-cat").textContent = c.categoria;
      const texto = document.getElementById("consejo-texto");
      texto.textContent = c.texto;
      caja.classList.add("consejo-nuevo");
      setTimeout(() => caja.classList.remove("consejo-nuevo"), 400);
    } catch { /* sin conexión: queda el consejo actual */ } finally { otro.disabled = false; }
  });
})();
