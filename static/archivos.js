// Campos para subir archivos: muestran qué se eligió antes de guardar.
document.querySelectorAll(".file-drop input[type=file]").forEach((input) => {
  const texto = input.nextElementSibling;
  const original = texto.textContent;
  input.addEventListener("change", () => {
    const n = input.files.length;
    texto.textContent = n ? (n === 1 ? `📎 ${input.files[0].name}` : `📎 ${n} archivos elegidos`) : original;
  });
});

// Botones «Copiar» genéricos: data-copiar="#id-del-texto".
document.querySelectorAll("[data-copiar]").forEach((b) => {
  b.addEventListener("click", async () => {
    const t = document.querySelector(b.dataset.copiar);
    try { await navigator.clipboard.writeText(t.textContent.trim()); b.textContent = "¡Copiado!"; }
    catch { b.textContent = "Copialo a mano"; }
  });
});
