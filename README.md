# GarajeData — Bitácora del automotor

App web (Python + Flask + SQLite) para llevar la historia completa de cada auto: services,
fluidos, piezas, accesorios, reparaciones, modificaciones, documentación y más. Cada persona
crea su cuenta y ve solo sus vehículos.

## Funciones

- Resumen de controles y vencimientos pendientes con acceso directo desde el inicio.
- Formulario único de Nuevo registro, con categorías agrupadas en Mantenimiento y cuidado, Gastos y papeles y Otro. Incluye Neumáticos, Chapa y pintura y Accesorios y modificaciones; Combustible pertenece a Gastos y papeles.
- Perfiles con imagen destacada y secciones desplegables; acceso móvil que acompaña el scroll.
- Gastos del mes frente al mismo tramo del anterior, importes faltantes y costo por km con lecturas fechadas y crecientes.
- Marca SVG en `static/img/logo.svg` y `logo-completo.svg` (letras en curvas). El paquete `exports/garajedata-marca.zip` incluye SVG, PNG de 4096 px y marca completa de 6000 px de ancho. Para regenerar: `tools/exportar_marca.py` (fonttools y brotli) y `tools/exportar_rasters.cjs` (sharp). Son herramientas de diseño, no dependencias del servidor.

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
- **Estadísticas**: gasto por mes y por categoría, promedio mensual y costo por km.
- **Calendario**: link para suscribirse desde Google Calendar, iPhone u Outlook y recibir los
  próximos services y vencimientos como eventos.
- **Transferir un vehículo** a otra cuenta con un código de un solo uso (por ejemplo, al venderlo).
- **Tus datos**: descargar todo en un .zip (JSON, planillas CSV y archivos) y borrar la cuenta.
- Diseño adaptado a celular e **instalable como app** (PWA).
- Seguridad: token CSRF en todos los formularios, límite de cuentas nuevas por IP y en total,
  bloqueo tras muchos intentos de ingreso.

## Probarla en tu PC

```bash
pip install -r requirements.txt
python app.py
```

Abrí http://127.0.0.1:5000. Los datos se guardan en `bitacora.db` y los archivos subidos en
`uploads/` (ninguno de los dos se sube a git). En Windows también sirve `Iniciar GarajeData.bat`.

Pruebas: `pytest` (corre `tools/probar_paginas.py`, que abre todas las páginas y formularios con
una base temporal y termina con `TODO OK`). En GitHub corren solas en cada push.

## Código

- `app.py`: punto de entrada; importa el núcleo y las páginas.
- `nucleo.py`: la app Flask, la base y sus migraciones, filtros, seguridad y funciones comunes.
- `rutas/`: las páginas, una por tema (`cuentas`, `vehiculos`, `registros`, `boveda`, `libro`,
  `estadisticas`, `transferir`, `datos`).
- `mantenimiento.py` (plan y vencimientos), `archivos.py` (subidas), `catalogo.py` (marcas y modelos).
- `static/vendor/`: three.js y las tipografías, alojados en el sitio (sin depender de CDN).

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
6. Copias de seguridad: la app copia la base sola una vez por día (con la primera visita) en
   `garajedata/respaldos/` y guarda las últimas 14. Para forzar una: `python3.13 tools/respaldo.py`.

> **Importante:** apenas la publiques, creá tu cuenta antes que nadie. La primera cuenta que se
> crea hereda los vehículos que ya estuvieran cargados en la base.

## Modelos 3D

Usa [three.js](https://threejs.org) (copia local en `static/vendor/three`) y modelos `.glb` en `static/models/tipos/`,
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
| `MAX_USUARIOS` | Tope de cuentas en total (por defecto 300).                        |
