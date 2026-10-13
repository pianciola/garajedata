# GarajeData — Bitácora del automotor

App web (Python + Flask + SQLite) para llevar la historia completa de cada auto: services,
fluidos, piezas, accesorios, reparaciones, modificaciones, documentación y más. Cada persona
crea su cuenta y ve solo sus vehículos.

## Funciones

- **Cuentas** con usuario y contraseña, sin email ni datos personales. La recuperación se hace con
  un código que se muestra una sola vez al crear la cuenta.
- **Vehículos** con modelo 3D girando según la carrocería y el color elegido, marca con logo,
  modelo, versión, apodo, patente (modelos de chapa vieja y Mercosur) y transmisión.
- **Ficha técnica** opcional: motor, combustible, tanque, código de pintura, VIN, aceite, bujías,
  refrigerante, líquido de frenos, neumáticos y presiones.
- **Bitácora**: registros por categoría con fecha, km, costo, quién lo hizo (taller, yo u otro),
  fotos y facturas adjuntas, buscador y filtros.
- **Avisos**: próximo control por km o fecha, y un plan de mantenimiento estimado según cuánto
  se usa el auto (poco, promedio o mucho).
- **Documentación**: vencimientos de VTV, seguro, matafuegos, patente y registro, con botón
  «ya lo pagué / renové».
- **Bóveda digital**: fotos y PDF de cédula, seguro y VTV, disponibles sin conexión.
- **Libro de servicio** en PDF y **link para compartir** la bitácora en modo solo lectura
  (nunca incluye documentación ni bóveda).
- Diseño adaptado a celular.

## Probarla en tu PC

```bash
pip install -r requirements.txt
python app.py
```

Abrí http://127.0.0.1:5000. Los datos se guardan en `bitacora.db` y los archivos subidos en
`uploads/` (ninguno de los dos se sube a git). En Windows también sirve `Iniciar GarajeData.bat`.

Prueba rápida de todas las páginas, con una base temporal: `python tools/probar_paginas.py`
(termina con `TODO OK`).

## Publicarla gratis en PythonAnywhere

1. Creá una cuenta gratis en https://www.pythonanywhere.com.
2. Armá el paquete: `python tools/armar_paquete.py TU_USUARIO` (agregá `--sin-base` para
   actualizar el código sin pisar los datos de la web). Genera en `para_subir/` un `.zip` y el
   archivo WSGI.
3. En **Files** subí el `.zip` y descomprimilo en una consola Bash:
   `unzip garajedata.zip -d garajedata`.
4. En **Web** creá una app **Manual configuration** (Python 3.13), apuntá **Source code** a
   `/home/TU_USUARIO/garajedata`, agregá el mapeo estático `/static/` →
   `/home/TU_USUARIO/garajedata/static`, y reemplazá el contenido del archivo WSGI por el
   generado. Activá **Force HTTPS** y tocá **Reload**.
5. El plan gratis pide tocar **«Run until 1 month from today»** en **Web** una vez por mes.

> **Importante:** apenas la publiques, creá tu cuenta antes que nadie. La primera cuenta que se
> crea hereda los vehículos que ya estuvieran cargados en la base.

## Modelos 3D

Usa [three.js](https://threejs.org) desde un CDN y modelos `.glb` en `static/models/tipos/`,
uno por carrocería. Salen del «Generic passenger car pack» de Comrade1280 (CC BY 4.0); ver
[static/models/LEEME.md](static/models/LEEME.md). Para regenerarlos: `tools/preparar_modelos.py`
y después `tools/separar_modelos.py`. Los logos de marcas son de
[car-logos-dataset](https://github.com/filippofilip95/car-logos-dataset).

## Configuración (variables de entorno)

| Variable     | Para qué sirve                                                       |
|--------------|----------------------------------------------------------------------|
| `SECRET_KEY` | Clave para firmar las sesiones. Obligatoria al publicarla.           |
| `DB_PATH`    | Ruta de la base de datos (por defecto `bitacora.db`).                |
| `UPLOAD_DIR` | Carpeta de archivos subidos (por defecto `uploads/`).                |
