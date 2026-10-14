# GarajeData

Bitácora del automotor: Flask + SQLite, en español rioplatense. Cada usuario ve solo sus vehículos.
Online: https://garajedata.pythonanywhere.com (cuenta `garajedata`, plan gratis).
Código: https://github.com/pianciola/garajedata (público, rama `main`).

## Estructura
- `app.py` entrada · `nucleo.py` app, base, migraciones, filtros, seguridad · `rutas/` una página por tema.
- `mantenimiento.py` plan y vencimientos · `archivos.py` subidas · `catalogo.py` marcas · `respaldos.py` backup diario.
- `templates/`, `static/` (`vendor/` = three.js y fuentes locales, sin CDN) · `tools/` scripts.

## Reglas de trabajo
- Responder siempre en español.
- Después de cada cambio: probar, **actualizar PythonAnywhere y GitHub**.
- Nunca poner contraseñas, claves ni datos personales en el repo. La app no pide email.
- Las migraciones de columnas van en `COLUMNAS_NUEVAS` / `init_db()` de `nucleo.py` (ALTER TABLE; nunca borrar datos).
- Todo formulario POST lleva `<input type="hidden" name="csrf" value="{{ csrf_token() }}">`;
  los `fetch` mandan el header `X-CSRF-Token` (meta `csrf` en `base.html`).
- CSP con nonce: todo `<script>` inline lleva `nonce="{{ csp_nonce }}"`; no usar `onclick=`/`onsubmit=` (usar `data-confirmar`, `data-imprimir` en `static/acciones.js`).
  Si se suma un recurso externo (imágenes, fuentes, scripts), agregarlo a `politica_csp()` en `nucleo.py`.
- En el sitio publicado el WSGI define `GARAJEDATA_HTTPS=1` (cookie Secure + HSTS); lo genera `tools/armar_paquete.py`.
- Los archivos subidos solo se sirven por rutas con chequeo de dueño; no exponer `uploads/`.

## Probar
```bash
python -m pytest -q            # probar_paginas.py ("TODO OK") + tools/auditoria.py (seguridad y robustez: 0 hallazgos)
python app.py                  # local en http://127.0.0.1:5000
```

## Desplegar (PythonAnywhere)
1. `python tools/armar_paquete.py garajedata --sin-base` → `para_subir/garajedata.zip` (**sin base**, para no pisar datos).
2. Subir el zip a `/home/garajedata/` (pestaña Files).
3. En la consola Bash: `cp garajedata/bitacora.db bitacora_respaldoN.db && unzip -oq garajedata.zip -d garajedata`.
4. Reiniciar: `touch /var/www/garajedata_pythonanywhere_com_wsgi.py` o botón Reload en Web.
   El primer Reload a veces no aplica: esperar ~20 s y verificar con `curl` + parámetro anti-caché.
- Plan gratis: sin tareas programadas, máx. 2 consolas.
  **Renovar cada mes** con «Run until 1 month from today» (vence ~13/11/2026) o el sitio se apaga.
- La primera cuenta creada hereda los vehículos sin dueño (ya está creada: `juanpianciola`).

## Detalles que conviene recordar
- Chrome: el comando tipeado en la consola de PythonAnywhere a veces no corre (pantalla vieja); repetirlo y revisar la hora.
- Capturas locales: Edge headless; no baja de ~500 px de ancho (usar iframe).
- Logo: `static/img/logo-icono.png`, macro `templates/_logo.html`.
- Textos legales en `legal.py` (adaptados de MacroCenter, fecha en `ACTUALIZACION`): si cambia qué datos
  guarda o a quién se los muestra la app, **actualizar ese texto**. Crear cuenta exige aceptarlos.
