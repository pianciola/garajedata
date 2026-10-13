// Campos para subir archivos: muestran qué se eligió antes de guardar.
document.querySelectorAll(".file-drop input[type=file]").forEach((input) => {
  const texto = input.nextElementSibling;
  const original = texto.textContent;
  input.addEventListener("change", () => {
    const n = input.files.length;
    texto.textContent = n ? (n === 1 ? `📎 ${input.files[0].name}` : `📎 ${n} archivos elegidos`) : original;
  });
});
