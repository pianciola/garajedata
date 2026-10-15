(() => {
  const atajo = document.getElementById('servicio-atajo');
  if (!atajo) return;
  const actualizar = () => {
    atajo.hidden = document.querySelector('input[name="tipo"]:checked')?.value !== 'service';
  };
  document.querySelectorAll('input[name="tipo"]').forEach(input => input.addEventListener('change', actualizar));
  actualizar();
})();
