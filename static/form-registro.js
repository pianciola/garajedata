// Formulario de registro: elige la categoría sola según lo que se escribe en
// "¿Qué se hizo?" (ej: "cambio de aceite" -> Cambio de fluidos).
(() => {
  // Se revisan en este orden: la primera regla con una palabra presente gana.
  // Por eso "pérdida de aceite" cae en Reparación antes que en Fluidos.
  const REGLAS = [
    ["combustible", ["carga de nafta", "carga de combustible", "carga de gnc", "carga de diesel", "cargar nafta"]],
    ["reparacion", ["arreglo", "reparacion", "reparar", "perdida", "fuga", "rectific", "soldad", "chapa",
                    "choque", "abolladura", "falla", "ruido", "electricidad", "cortocircuito", "repar"]],
    ["accesorios", ["accesorio", "alfombra", "cubre", "funda", "estereo", "stereo", "radio", "parlante",
                    "portaequipaje", "barras de techo", "camara", "sensor de estacionamiento", "alarma",
                    "enganche", "gancho", "matafuego", "baliza", "cargador", "soporte", "cobertor", "lona",
                    "dashcam", "gps", "botiquin", "toldo", "cofre"]],
    ["modificacion", ["modificacion", "deportiv", "tuning", "reprogram", "remap", "chip", "stage",
                      "polarizad", "vinilo", "ploteo", "coilover", "rebaje", "admision",
                      "intercooler", "spoiler", "aleron", "suspension regulable", "led", "xenon",
                      "downpipe", "llantas deportivas"]],
    // Controles inconfundibles, antes de las piezas ("presión de neumáticos" es un control).
    ["control", ["vtv", "itv", "alineacion", "balanceo", "rotacion", "diagnostico", "escaneo", "presion"]],
    ["fluidos", ["aceite", "refrigerante", "anticongelante", "liquido", "fluido", "atf", "valvulina",
                 "agua destilada", "lavaparabrisas", "aditivo", "gas del aire", "carga de aire"]],
    ["piezas", ["pastilla", "disco", "correa", "distribucion", "bujia", "bateria", "neumatico", "cubierta",
                "goma", "amortiguador", "embrague", "filtro", "rotula", "bomba", "buje", "cazoleta",
                "escobilla", "limpiaparabrisas", "lampara", "foco", "bieleta", "extremo", "homocinetica",
                "radiador", "termostato", "tensor", "rodamiento", "ruleman", "parrilla", "axial", "cable",
                "sensor", "inyector", "bobina", "alternador", "burro", "arranque", "escape", "silenciador",
                "manguera", "junta", "llanta", "espejo", "optica", "cerradura", "bocina"]],
    ["control", ["service", "revision", "inspeccion", "control", "chequeo", "verificacion"]],
    ["otro", ["lavado", "limpieza", "pulido", "patente", "seguro", "multa", "estacionamiento", "peaje",
              "transferencia", "cochera"]],
  ];

  const norm = (t) => (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  function detectar(texto) {
    const t = norm(texto);
    for (const [categoria, palabras] of REGLAS) {
      if (palabras.some((p) => t.includes(p))) return categoria;
    }
    return null;
  }

  const titulo = document.getElementById("titulo");
  const aviso = document.getElementById("aviso-categoria");
  // Última categoría puesta automáticamente: si el usuario la cambia a mano,
  // no se la pisa mientras el texto siga indicando lo mismo.
  let ultimaAuto = detectar(titulo.value);

  titulo.addEventListener("input", () => {
    const cat = detectar(titulo.value);
    if (!cat || cat === ultimaAuto) return;
    ultimaAuto = cat;
    const radio = document.querySelector(`input[name=categoria][value="${cat}"]`);
    if (!radio || radio.checked) return;
    radio.checked = true;
    aviso.textContent = `Detectado automáticamente: ${radio.nextElementSibling.textContent}`;
    aviso.hidden = false;
    aviso.classList.remove("flash-in");
    void aviso.offsetWidth; // reinicia la animación
    aviso.classList.add("flash-in");
  });

  // Si el usuario elige otra categoría a mano, el aviso ya no corresponde.
  document.querySelectorAll("input[name=categoria]").forEach((r) =>
    r.addEventListener("change", () => { aviso.hidden = true; }));
})();

// "¿Quién lo hizo?": el nombre solo se pide para un taller (opcional) o para "Otro".
(() => {
  const select = document.getElementById("hecho-por");
  const campo = document.getElementById("campo-quien");
  if (!select || !campo) return;
  const etiqueta = document.getElementById("etiqueta-quien");
  const input = document.getElementById("taller");
  select.addEventListener("change", () => {
    const v = select.value;
    campo.hidden = !(v === "taller" || v === "otro");
    etiqueta.firstChild.textContent = v === "otro" ? "Nombre " : "Nombre del taller ";
    document.getElementById("opcional-quien").textContent = v === "otro" ? "" : "(opcional)";
    input.placeholder = v === "otro" ? "Ej: mi cuñado, el gomero de la esquina…" : "Ej: Lubricentro Juan, concesionario…";
    if (!campo.hidden) input.focus();
  });
})();

