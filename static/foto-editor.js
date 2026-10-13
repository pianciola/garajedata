// Editor de la foto del auto: elegir entre modelo 3D y foto propia, vista previa
// de la foto elegida y ajuste (zoom, posición, llenar el marco o ver completa).
// Se activa en cada [data-foto-editor]; lo usan el formulario del vehículo y la
// ventanita de la ficha.
(() => {
  function iniciar(raiz) {
    const $ = (s) => raiz.querySelector(s);
    const radios = raiz.querySelectorAll("input[name=imagen_modo]");
    const stage = $("[data-ed=stage]"), opciones = $("[data-ed=opciones]");
    const archivo = $("[data-ed=archivo]"), img = $("[data-ed=img]"), vacia = $("[data-ed=vacia]");
    const aviso3d = $("[data-ed=aviso3d]");
    const zoomTxt = $("[data-ed=zoomv]");
    const zoom = $("[name=foto_zoom]"), px = $("[name=foto_x]"), py = $("[name=foto_y]");
    const st3d = raiz.dataset.stage3d ? document.querySelector(raiz.dataset.stage3d) : null;
    const modo = () => raiz.querySelector("input[name=imagen_modo]:checked")?.value;

    function actualizar() {
      const foto = modo() === "foto";
      if (st3d) st3d.hidden = foto;
      stage.hidden = !foto;
      opciones.hidden = !foto;
      if (aviso3d) aviso3d.hidden = foto;
    }
    radios.forEach((r) => r.addEventListener("change", actualizar));

    archivo.addEventListener("change", () => {
      const f = archivo.files[0];
      if (!f) return;
      img.src = URL.createObjectURL(f);
      vacia.hidden = true;
    });
    const quitar = raiz.querySelector("input[name=quitar_foto]");
    if (quitar) quitar.addEventListener("change", () => { img.style.opacity = quitar.checked ? ".25" : ""; });

    function aplicarAjuste() {
      stage.style.setProperty("--fx", px.value + "%");
      stage.style.setProperty("--fy", py.value + "%");
      stage.style.setProperty("--fz", zoom.value / 100);
      zoomTxt.textContent = zoom.value + "%";
      stage.classList.toggle("foto-completa", raiz.querySelector("input[name=foto_ajuste]:checked")?.value === "completa");
    }
    [zoom, px, py].forEach((r) => r.addEventListener("input", aplicarAjuste));
    raiz.querySelectorAll("input[name=foto_ajuste]").forEach((m) => m.addEventListener("change", aplicarAjuste));
    $("[data-ed=reset]").addEventListener("click", () => {
      zoom.value = 100; px.value = 50; py.value = 50;
      raiz.querySelector("input[name=foto_ajuste][value=cubrir]").checked = true;
      aplicarAjuste();
    });

    // Arrastrar la foto sobre la vista previa.
    let arrastre = null;
    stage.addEventListener("pointerdown", (e) => {
      if (e.button > 0 || !img.getAttribute("src")) return;
      arrastre = { x: e.clientX, y: e.clientY, fx: +px.value, fy: +py.value };
      stage.setPointerCapture(e.pointerId);
      stage.classList.add("arrastrando");
    });
    stage.addEventListener("pointermove", (e) => {
      if (!arrastre) return;
      const caja = stage.getBoundingClientRect(), z = zoom.value / 100;
      // Mover la foto hacia un lado muestra más del lado contrario.
      px.value = Math.min(100, Math.max(0, arrastre.fx - (e.clientX - arrastre.x) / caja.width * 100 / z));
      py.value = Math.min(100, Math.max(0, arrastre.fy - (e.clientY - arrastre.y) / caja.height * 100 / z));
      aplicarAjuste();
    });
    const soltar = () => { arrastre = null; stage.classList.remove("arrastrando"); };
    stage.addEventListener("pointerup", soltar);
    stage.addEventListener("pointercancel", soltar);

    actualizar();
    aplicarAjuste();
  }
  document.querySelectorAll("[data-foto-editor]").forEach(iniciar);
})();
