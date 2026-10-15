// Formulario de vehículo: desplegables de marca (con logo) y modelo, y selector de color.
(() => {
  const { marcas: CATALOGO, versionesGenericas } = JSON.parse(document.getElementById("catalogo").textContent);
  const MARCAS = Object.keys(CATALOGO);
  const norm = (t) => (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  const marcaDe = (t) => MARCAS.find((m) => norm(m) === norm(t));

  // Combobox: lista filtrable que también acepta texto libre.
  function combo(root, { opciones, alElegir, vacio }) {
    const input = root.querySelector("input");
    const list = root.querySelector(".combo-list");
    let activo = -1;

    // filtrar = false al abrir el desplegable (se ven todas); true mientras se escribe.
    function render(filtrar) {
      const f = filtrar ? norm(input.value) : "";
      const todas = opciones();
      // Primero las que empiezan con lo escrito, después las que lo contienen.
      const items = [
        ...todas.filter((o) => norm(o.valor).startsWith(f)),
        ...todas.filter((o) => !norm(o.valor).startsWith(f) && norm(o.valor).includes(f)),
      ];
      list.innerHTML = "";
      for (const o of items) {
        const li = document.createElement("li");
        li.setAttribute("role", "option");
        li.dataset.value = o.valor;
        if (o.logo) {
          const img = document.createElement("img");
          img.src = o.logo;
          img.alt = "";
          img.loading = "lazy";
          if (o.oscuro) img.classList.add("logo-oscuro");
          li.appendChild(img);
        }
        const span = document.createElement("span");
        span.textContent = o.valor;
        li.appendChild(span);
        if (o.detalle) {
          const small = document.createElement("small");
          small.textContent = o.detalle;
          li.appendChild(small);
        }
        li.addEventListener("mousedown", (e) => { e.preventDefault(); elegir(o); });
        list.appendChild(li);
      }
      if (!items.length) {
        const li = document.createElement("li");
        li.className = "combo-empty";
        li.textContent = todas.length ? "Sin coincidencias: se guarda como lo escribiste" : vacio;
        list.appendChild(li);
      }
      activo = -1;
    }
    const abrir = (filtrar = false) => { render(filtrar); list.hidden = false; input.setAttribute("aria-expanded", "true"); };
    const cerrar = () => { list.hidden = true; input.setAttribute("aria-expanded", "false"); };
    function elegir(o) {
      input.value = o.valor;
      cerrar();
      alElegir?.(o);
      input.dispatchEvent(new Event("change"));
    }
    function marcar(i) {
      const opts = list.querySelectorAll("li[data-value]");
      if (!opts.length) return;
      activo = (i + opts.length) % opts.length;
      opts.forEach((o, j) => o.classList.toggle("active", j === activo));
      opts[activo].scrollIntoView({ block: "nearest" });
    }

    input.addEventListener("focus", () => abrir(false));
    input.addEventListener("input", () => abrir(true));
    input.addEventListener("blur", () => {
      cerrar();
      // Si coincide con una opción ("ford", "megane"), se escribe como en el catálogo.
      const o = opciones().find((x) => norm(x.valor) === norm(input.value));
      // Solo corrige el texto: no cambia la carrocería que el usuario haya elegido.
      if (o && o.valor !== input.value) {
        input.value = o.valor;
        input.dispatchEvent(new Event("change"));
      }
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); if (list.hidden) abrir(true); marcar(activo + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); marcar(activo - 1); }
      else if (e.key === "Enter" && !list.hidden && activo >= 0) {
        e.preventDefault();
        const valor = list.querySelectorAll("li[data-value]")[activo].dataset.value;
        elegir(opciones().find((o) => o.valor === valor));
      } else if (e.key === "Escape") cerrar();
    });
    root.querySelector(".combo-toggle").addEventListener("mousedown", (e) => {
      e.preventDefault();
      if (list.hidden) input.focus(); else cerrar();
    });
    return input;
  }

  // Marca
  const rootMarca = document.getElementById("combo-marca");
  const logo = rootMarca.querySelector(".combo-logo");
  const inputMarca = combo(rootMarca, {
    opciones: () => MARCAS.map((m) => ({ valor: m, logo: CATALOGO[m].logo, oscuro: CATALOGO[m].oscuro })),
  });
  function actualizarLogo() {
    const m = marcaDe(inputMarca.value);
    logo.hidden = !m;
    rootMarca.classList.toggle("has-logo", !!m);
    if (m) {
      logo.src = CATALOGO[m].logo;
      logo.classList.toggle("logo-oscuro", CATALOGO[m].oscuro);
    }
  }
  inputMarca.addEventListener("input", actualizarLogo);
  inputMarca.addEventListener("change", actualizarLogo);
  actualizarLogo();

  // Modelo: depende de la marca; al elegirlo se marca su carrocería.
  const NOMBRES_CARROCERIA = Object.fromEntries(
    [...document.querySelectorAll("input[name=carroceria]")].map((r) => [r.value, r.nextElementSibling.textContent]));
  combo(document.getElementById("combo-modelo"), {
    opciones: () => {
      const m = marcaDe(inputMarca.value);
      return m ? CATALOGO[m].modelos.map(([valor, tipo]) => ({ valor, tipo, detalle: NOMBRES_CARROCERIA[tipo] })) : [];
    },
    vacio: "Elegí primero una marca de la lista, o escribí el modelo",
    alElegir: (o) => {
      const radio = document.querySelector(`input[name=carroceria][value="${o.tipo}"]`);
      if (radio && !radio.checked) {
        radio.checked = true;
        radio.dispatchEvent(new Event("change"));
      }
    },
  });

  // Generación: las del modelo elegido más las genéricas (pre-restyling / restyling).
  const inputModelo = document.getElementById("modelo");
  combo(document.getElementById("combo-version"), {
    opciones: () => {
      const m = marcaDe(inputMarca.value);
      const versiones = m ? (CATALOGO[m].versiones[inputModelo.value] || []) : [];
      return [...versiones, ...versionesGenericas].map((valor) => ({ valor }));
    },
  });

  // Versión de equipamiento (LT, LTZ, Ghia…): las conocidas del modelo; se puede escribir cualquier otra.
  combo(document.getElementById("combo-equipamiento"), {
    opciones: () => {
      const m = marcaDe(inputMarca.value);
      return (m ? (CATALOGO[m].equipamientos[inputModelo.value] || []) : []).map((valor) => ({ valor }));
    },
    vacio: "Escribí la versión (la que figura en la tapa del baúl o en los papeles)",
  });

  // Color
  const colorInput = document.getElementById("color");
  const swatches = document.querySelectorAll(".swatch");
  const marcarColor = () => swatches.forEach((s) => s.classList.toggle("active", s.dataset.color === colorInput.value.toLowerCase()));
  swatches.forEach((s) => s.addEventListener("click", () => {
    colorInput.value = s.dataset.color;
    colorInput.dispatchEvent(new Event("input"));
  }));
  colorInput.addEventListener("input", marcarColor);
})();

// Plan de mantenimiento: los perfiles de uso solo se eligen con la casilla tildada.
(() => {
  const casilla = document.getElementById("calcular-uso");
  const perfiles = document.getElementById("uso-picker");
  if (!casilla || !perfiles) return;
  const actualizar = () => perfiles.classList.toggle("apagado", !casilla.checked);
  const kmMes = document.getElementById("km-mes");
  const personalizado = document.querySelector("input[name=uso][value=personalizado]");
  if (kmMes && personalizado) {
    // Escribir los km por mes elige solo la opción "Personalizado".
    kmMes.addEventListener("focus", () => { personalizado.checked = true; });
    kmMes.addEventListener("input", () => { personalizado.checked = true; });
    const medido = document.getElementById("usar-medido");
    if (medido) medido.addEventListener("click", () => {
      casilla.checked = true; actualizar();
      personalizado.checked = true;
      kmMes.value = Number(medido.dataset.km).toLocaleString("es-AR");
    });
  }
  casilla.addEventListener("change", actualizar);
  perfiles.addEventListener("click", () => {
    if (!casilla.checked) { casilla.checked = true; actualizar(); }
  });
  actualizar();
})();
