// Campos numéricos con punto de miles mientras se escribe: 21000 -> 21.000.
// <input class="num-miles">; con data-decimales acepta coma y 2 decimales (1.234,50).
(() => {
  function formatear(valor, decimales) {
    const coma = decimales ? valor.indexOf(",") : -1;
    let entero = (coma >= 0 ? valor.slice(0, coma) : valor).replace(/\D/g, "");
    entero = entero.replace(/^0+(?=\d)/, "");
    let texto = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    if (coma >= 0) texto = (texto || "0") + "," + valor.slice(coma + 1).replace(/\D/g, "").slice(0, 2);
    return texto;
  }

  // Cuántos dígitos o comas hay antes de la posición pos (los puntos no cuentan).
  const significativos = (texto, pos) => (texto.slice(0, pos).match(/[\d,]/g) || []).length;

  function alEscribir(e) {
    const input = e.target;
    // En campos con decimales, un punto tipeado a mano se toma como coma decimal.
    if (e.data === "." && "decimales" in input.dataset && !input.value.includes(",")) {
      const p = input.selectionStart;
      input.value = input.value.slice(0, p - 1) + "," + input.value.slice(p);
      input.setSelectionRange(p, p);
    }
    const antes = significativos(input.value, input.selectionStart);
    const nuevo = formatear(input.value, "decimales" in input.dataset);
    if (nuevo === input.value) return;
    input.value = nuevo;
    // Deja el cursor después del mismo dígito en el que estaba.
    let pos = 0, contados = 0;
    while (pos < nuevo.length && contados < antes) {
      if (/[\d,]/.test(nuevo[pos])) contados++;
      pos++;
    }
    input.setSelectionRange(pos, pos);
  }

  for (const input of document.querySelectorAll("input.num-miles")) {
    input.addEventListener("input", alEscribir);
    input.value = formatear(input.value, "decimales" in input.dataset);
  }
})();
