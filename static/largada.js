// Easter egg: largada de Fórmula 1 con test de reflejos.
// Se activa tocando 3 veces seguidas la bandera a cuadros del pie, o con el código Konami (↑↑↓↓←→←→BA).
(() => {
  const CLAVE = "garaje-largada-record";
  let abierto = false;

  // ---------- disparadores
  const bandera = document.querySelector("[data-largada]");
  let toques = [];
  bandera?.addEventListener("click", () => {
    const ahora = Date.now();
    toques = [...toques.filter((t) => ahora - t < 1500), ahora];
    if (toques.length >= 3) { toques = []; abrir(); }
  });
  const KONAMI = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"];
  let paso = 0;
  document.addEventListener("keydown", (e) => {
    if (abierto) return;
    const tecla = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    paso = tecla === KONAMI[paso] ? paso + 1 : (tecla === KONAMI[0] ? 1 : 0);
    if (paso === KONAMI.length) { paso = 0; abrir(); }
  });

  // ---------- sonido (pitidos sintetizados, sin archivos)
  let audio = null;
  const pitido = (frec, dur) => {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const osc = audio.createOscillator(), vol = audio.createGain();
      osc.type = "square"; osc.frequency.value = frec;
      vol.gain.setValueAtTime(0.06, audio.currentTime);
      vol.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + dur);
      osc.connect(vol).connect(audio.destination);
      osc.start(); osc.stop(audio.currentTime + dur);
    } catch { /* sin audio: se juega igual */ }
  };

  const leerRecord = () => { try { return parseFloat(localStorage.getItem(CLAVE)) || null; } catch { return null; } };
  const guardarRecord = (t) => { try { localStorage.setItem(CLAVE, String(t)); } catch { /* sin almacenamiento */ } };
  const seg = (ms) => (ms / 1000).toFixed(3).replace(".", ",") + " s";
  const veredicto = (ms) => ms < 200 ? "Reflejos de piloto de F1 🏆" : ms < 280 ? "¡Muy buena largada! 🏁"
    : ms < 400 ? "Nada mal, pero en la pole no estás 😉" : "¿Te quedaste en boxes? 🐢";

  // ---------- el juego
  function abrir() {
    if (abierto) return;
    abierto = true;
    const capa = document.createElement("div");
    capa.className = "largada";
    capa.setAttribute("role", "dialog");
    capa.setAttribute("aria-label", "Largada: test de reflejos");
    capa.innerHTML = `
      <div class="largada-caja">
        <p class="largada-titulo">Modo largada</p>
        <div class="largada-luces">${"<span><i></i><i></i></span>".repeat(5)}</div>
        <p class="largada-texto">Tocá la pantalla (o cualquier tecla) cuando <b>se apaguen</b> las luces.</p>
        <p class="largada-record"></p>
        <div class="largada-botones" hidden>
          <button type="button" class="btn btn-primary" data-otra>Otra vez</button>
          <button type="button" class="btn btn-ghost" data-salir>Salir</button>
        </div>
      </div>`;
    document.body.appendChild(capa);
    const luces = capa.querySelectorAll(".largada-luces span");
    const texto = capa.querySelector(".largada-texto");
    const record = capa.querySelector(".largada-record");
    const botones = capa.querySelector(".largada-botones");
    let timers = [], estado = "espera", apagadas = 0;

    const mostrarRecord = () => {
      const r = leerRecord();
      record.textContent = r ? `Tu récord: ${seg(r)}` : "";
    };
    const limpiar = () => { timers.forEach(clearTimeout); timers = []; };
    const salir = () => {
      limpiar(); capa.remove(); abierto = false;
      document.removeEventListener("keydown", tecla, true);
    };
    const largar = () => {
      limpiar();
      estado = "luces"; botones.hidden = true; capa.classList.remove("largada-falsa", "largada-ok");
      texto.innerHTML = "Tocá la pantalla (o cualquier tecla) cuando <b>se apaguen</b> las luces.";
      luces.forEach((l) => l.classList.remove("on"));
      luces.forEach((l, n) => timers.push(setTimeout(() => { l.classList.add("on"); pitido(440, 0.12); }, 900 + n * 1000)));
      // Las luces se apagan entre 0,2 y 3 segundos después de la quinta, como en una largada real.
      timers.push(setTimeout(() => {
        luces.forEach((l) => l.classList.remove("on"));
        pitido(880, 0.25);
        estado = "carrera"; apagadas = performance.now();
      }, 900 + 4 * 1000 + 200 + Math.random() * 2800));
    };
    const reaccionar = () => {
      if (estado === "luces") {
        limpiar(); estado = "fin";
        capa.classList.add("largada-falsa");
        texto.innerHTML = "<b>¡Largada en falso!</b> Te toca drive-through 😅";
      } else if (estado === "carrera") {
        const ms = performance.now() - apagadas;
        estado = "fin";
        capa.classList.add("largada-ok");
        const anterior = leerRecord();
        const nuevo = !anterior || ms < anterior;
        if (nuevo) guardarRecord(ms);
        texto.innerHTML = `<span class="largada-tiempo">${seg(ms)}</span>${veredicto(ms)}${nuevo && anterior ? "<br><b>¡Nuevo récord!</b>" : ""}`;
      } else {
        return;
      }
      mostrarRecord();
      botones.hidden = false;
    };
    function tecla(e) {
      if (e.key === "Escape") { salir(); return; }
      if (estado !== "fin" && !e.repeat) { e.preventDefault(); reaccionar(); }
    }
    capa.addEventListener("pointerdown", (e) => {
      if (e.target.closest("[data-otra]")) { largar(); return; }
      if (e.target.closest("[data-salir]")) { salir(); return; }
      reaccionar();
    });
    document.addEventListener("keydown", tecla, true);
    mostrarRecord();
    largar();
  }
})();
