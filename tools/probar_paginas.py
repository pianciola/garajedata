"""Prueba rápida: abre todas las páginas y formularios con una base temporal.

Uso:  python tools/probar_paginas.py
No toca bitacora.db. Termina con "TODO OK" o lista lo que falló.
"""
import io
import os
from datetime import date, timedelta
import re
import sqlite3
import sys
import tempfile

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
DB = os.path.join(tempfile.mkdtemp(), "prueba.db")
os.environ["DB_PATH"] = DB
os.environ["UPLOAD_DIR"] = os.path.join(os.path.dirname(DB), "uploads")

# Base "vieja", de antes de las cuentas: un vehículo sin dueño.
with sqlite3.connect(DB) as db:
    db.execute("CREATE TABLE vehiculos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, "
               "marca TEXT, modelo TEXT, anio INTEGER, patente TEXT, km_inicial INTEGER, notas TEXT)")
    db.execute("INSERT INTO vehiculos (nombre, marca, modelo) VALUES ('', 'Ford', 'Focus')")

from app import app  # noqa: E402

# Las pruebas mandan formularios sin el token CSRF; más abajo se prueba aparte.
app.config["CSRF_APAGADO"] = True
import nucleo  # noqa: E402
nucleo.MAX_ALTAS_IP = 100  # muchas cuentas de prueba desde la misma "IP"

c = app.test_client()
fallas = []


def esperar(nombre, respuesta, codigo):
    if respuesta.status_code != codigo:
        fallas.append(f"{nombre}: esperaba {codigo}, dio {respuesta.status_code}")
    return respuesta


# Sin cuenta: bienvenida y redirección al ingreso
esperar("bienvenida", c.get("/"), 200)
if not os.path.exists(os.path.join(os.path.dirname(DB), "respaldos")):
    fallas.append("no se hizo el respaldo diario")
esperar("registro form", c.get("/registro"), 200)
esperar("login form", c.get("/login"), 200)
esperar("vehículo sin cuenta", c.get("/vehiculo/1"), 302)
esperar("alta sin cuenta", c.post("/vehiculo/nuevo", data={}), 302)

# Registro: errores y alta. La primera cuenta se queda con el vehículo viejo.
esperar("usuario corto", c.post("/registro", data={"acepto": "1", "usuario": "ab", "clave": "clave-123", "clave2": "clave-123"}), 200)
esperar("claves distintas", c.post("/registro", data={"acepto": "1", "usuario": "juan", "clave": "clave-123", "clave2": "x"}), 200)
esperar("registro ok", c.post("/registro", data={"acepto": "1", "usuario": "juan", "clave": "clave-123", "clave2": "clave-123"}), 302)
esperar("vehículo heredado", c.get("/vehiculo/1"), 200)

# Vehículo vacío y vehículo completo
esperar("alta vacía", c.post("/vehiculo/nuevo", data={}), 302)
esperar("alta completa", c.post("/vehiculo/nuevo", data={
    "marca": "ford", "modelo": "focus", "version": "MK1", "anio": "2006", "patente": "abc123",
    "km_inicial": "129.500", "carroceria": "hatchback", "color": "#c0262d", "transmision": "manual"}), 302)

# Registros: nuevo, con datos, con error de validación
for vid in (2, 3):
    esperar(f"form registro nuevo v{vid}", c.get(f"/vehiculo/{vid}/registro/nuevo"), 200)
esperar("registro completo", c.post("/vehiculo/3/registro/nuevo", data={
    "titulo": "Cambio de aceite", "categoria": "fluidos", "fecha": "2026-01-10", "km": "130.000",
    "costo": "85.000,50", "prox_km": "140.000", "prox_fecha": "2027-01-10"}), 302)
esperar("registro sin título", c.post("/vehiculo/3/registro/nuevo", data={"titulo": ""}), 200)

paginas = ["/", "/vehiculo/2", "/vehiculo/3", "/vehiculo/nuevo", "/vehiculo/2/editar", "/vehiculo/3/editar",
           "/vehiculo/3/registro/nuevo?cat=piezas", "/registro/1/editar", "/vehiculo/3/exportar",
           "/vehiculo/3?cat=fluidos&q=aceite"]
for p in paginas:
    esperar(p, c.get(p), 200)
esperar("404", c.get("/vehiculo/999"), 404)
esperar("editar registro con error", c.post("/registro/1/editar", data={"titulo": ""}), 200)

# Ficha técnica, fluidos y plan de mantenimiento

esperar("ficha completa", c.post("/vehiculo/3/editar", data={
    "marca": "Ford", "modelo": "Focus", "km_inicial": "129.500", "motor": "1.6 Zetec", "combustible": "nafta",
    "tanque": "55", "codigo_pintura": "3CSE", "vin": "8af-za12 3456789012", "aceite": "5W-30",
    "aceite_litros": "4,3", "bujias": "NGK", "refrigerante": "G12", "frenos": "DOT 4",
    "neumaticos": "205/55 R16", "presion_del": "32 psi", "presion_tras": "30 psi",
    "calcular_uso": "1", "uso": "mucho"}), 302)
html = esperar("vehículo con plan", c.get("/vehiculo/3"), 200).get_data(as_text=True)
for texto in ("Ficha técnica", "8AFZA123456789012", "4,30 L con filtro", "estimado", "Bujías"):
    if texto not in html:
        fallas.append(f"falta en la ficha: {texto}")
esperar("editar con promedio", c.get("/vehiculo/3/editar"), 200)
esperar("km por mes propios", c.post("/vehiculo/3/editar", data={"marca": "Ford", "modelo": "Focus", "km_inicial": "129.500",
    "calcular_uso": "1", "uso": "personalizado", "km_mes": "1.800"}), 302)
html = c.get("/vehiculo/3/editar").get_data(as_text=True)
if 'value="1.800"' not in html or 'value="personalizado" checked' not in html:
    fallas.append("no se guardó el perfil personalizado")
esperar("personalizado sin km", c.post("/vehiculo/3/editar", data={"marca": "Ford", "modelo": "Focus",
    "calcular_uso": "1", "uso": "personalizado", "km_mes": ""}), 302)
if 'value="personalizado" checked' in c.get("/vehiculo/3/editar").get_data(as_text=True):
    fallas.append("aceptó personalizado sin km por mes")
esperar("volver a mucho", c.post("/vehiculo/3/editar", data={"marca": "Ford", "modelo": "Focus", "km_inicial": "129.500",
    "calcular_uso": "1", "uso": "mucho"}), 302)
esperar("sin plan", c.post("/vehiculo/2/editar", data={"uso": "poco"}), 302)

# Documentación y vencimientos
esperar("form documentos", c.get("/vehiculo/3/documentos"), 200)
esperar("guardar documentos", c.post("/vehiculo/3/documentos", data={
    "vence_vtv": (date.today() - timedelta(days=40)).isoformat(), "cada_vtv": "1", "vence_seguro_pago": (date.today() + timedelta(days=200)).isoformat(), "cada_seguro_pago": "1",
    "detalle_seguro": "La Segunda", "vence_registro": "fecha mala"}), 302)
html = c.get("/vehiculo/3").get_data(as_text=True)
if "Venció hace" not in html or "La Segunda" not in html:
    fallas.append("no se ven los vencimientos")
html = c.get("/").get_data(as_text=True)
if "Próximo control" not in html or "Gastado" in html or "prox-vencido" not in html and "prox-pronto" not in html and "prox-ok" not in html:
    fallas.append("la tarjeta no muestra el próximo control")
if "avisos" not in c.get("/").get_data(as_text=True):
    fallas.append("la tarjeta no muestra avisos")
esperar("renovar vtv", c.post("/documento/1/renovar"), 302)

# Bóveda y adjuntos
def png(ancho=40, alto=30):
    """PNG válido armado a mano (no hace falta Pillow para la prueba)."""
    import struct
    import zlib

    def trozo(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))
    filas = b"".join(b"\x00" + b"\xc0\x26\x2d" * ancho for _ in range(alto))
    return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
            + trozo(b"IDAT", zlib.compress(filas)) + trozo(b"IEND", b""))


PNG = png()
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
esperar("subir a bóveda", c.post("/vehiculo/3/boveda", content_type="multipart/form-data", data={
    "categoria": "cedula", "archivos": [(io.BytesIO(PNG), "cedula.png"), (io.BytesIO(PDF), "seguro.pdf"),
                                        (io.BytesIO(b"MZ hola"), "virus.exe")]}), 302)
esperar("ver archivo", c.get("/archivo/1"), 200)
esperar("ver pdf", c.get("/archivo/2"), 200)
esperar("archivo inexistente", c.get("/archivo/3"), 404)
esperar("registro con adjunto", c.post("/vehiculo/3/registro/nuevo", content_type="multipart/form-data", data={
    "titulo": "Bujías", "categoria": "piezas", "fecha": "2026-02-01", "km": "131.000", "hecho_por": "otro",
    "taller": "Mi cuñado", "archivos": [(io.BytesIO(PNG), "factura.png")]}), 302)
html = c.get("/vehiculo/3").get_data(as_text=True)
if "Mi cuñado" not in html or "/archivo/3" not in html:
    fallas.append("el registro no muestra quién lo hizo o su foto")
esperar("registro hecho por mí", c.post("/vehiculo/3/registro/nuevo", data={
    "titulo": "Lavado", "hecho_por": "yo", "taller": "no se guarda"}), 302)
if "no se guarda" in c.get("/vehiculo/3").get_data(as_text=True):
    fallas.append("hecho por mí guardó un nombre")
esperar("editar registro con adjunto", c.get("/registro/2/editar"), 200)

# Libro de servicio y compartir
esperar("libro", c.get("/vehiculo/3/libro"), 200)
esperar("compartir form", c.get("/vehiculo/3/compartir"), 200)
esperar("activar link", c.post("/vehiculo/3/compartir", data={"accion": "activar"}), 302)
html = c.get("/vehiculo/3/compartir").get_data(as_text=True)
token = re.search(r'id="link">[^<]*/c/([\w-]+)<', html).group(1)
esperar("service worker", c.get("/sw.js"), 200)

# Foto propia en lugar del modelo 3D
esperar("foto sin archivo", c.post("/vehiculo/3/editar", data={"imagen_modo": "foto"}), 302)
if 'class="car-stage car-photo' in c.get("/vehiculo/3").get_data(as_text=True):
    fallas.append("mostró foto sin tener una")
esperar("foto pdf rechazada", c.post("/vehiculo/3/editar", content_type="multipart/form-data", data={
    "imagen_modo": "foto", "foto": (io.BytesIO(PDF), "x.pdf")}), 302)
esperar("foto ok", c.post("/vehiculo/3/editar", content_type="multipart/form-data", data={
    "imagen_modo": "foto", "foto": (io.BytesIO(PNG), "auto.png")}), 302)
for pagina in ("/vehiculo/3", "/", "/vehiculo/3/libro", "/vehiculo/3/editar"):
    if "car-photo" not in c.get(pagina).get_data(as_text=True):
        fallas.append(f"no se ve la foto en {pagina}")
fid = int(re.search(r"/archivo/(\d+)\" alt=\"Foto de", c.get("/vehiculo/3").get_data(as_text=True)).group(1))
esperar("servir foto", c.get(f"/archivo/{fid}"), 200)
if "auto.png" in c.get("/vehiculo/3").get_data(as_text=True).split("Bóveda digital")[1]:
    fallas.append("la foto del auto aparece en la bóveda")
esperar("ajustar foto", c.post("/vehiculo/3/editar", data={"imagen_modo": "foto", "foto_x": "20", "foto_y": "80",
    "foto_zoom": "150", "foto_ajuste": "completa"}), 302)
html = c.get("/vehiculo/3").get_data(as_text=True)
if "--fx: 20%" not in html or "--fy: 80%" not in html or "--fz: 1.5" not in html or "foto-completa" not in html:
    fallas.append("no se aplicó el ajuste de la foto")
esperar("ajuste fuera de rango", c.post("/vehiculo/3/editar", data={"imagen_modo": "foto", "foto_x": "999", "foto_y": "-5",
    "foto_zoom": "9000", "foto_ajuste": "x"}), 302)
html = c.get("/vehiculo/3").get_data(as_text=True)
if "--fx: 100%" not in html or "--fz: 3.0" not in html or "foto-completa" in html:
    fallas.append("el ajuste fuera de rango no se limitó")
html = c.get("/vehiculo/3").get_data(as_text=True)
if 'id="abrir-foto"' not in html or 'action="/vehiculo/3/foto"' not in html:
    fallas.append("falta el botón o la ventanita para editar la foto desde la ficha")
esperar("foto desde la ficha", c.post("/vehiculo/3/foto", content_type="multipart/form-data", data={
    "imagen_modo": "foto", "foto_zoom": "200", "foto_x": "10", "foto_y": "90", "foto_ajuste": "cubrir",
    "foto": (io.BytesIO(PNG), "nueva.png")}), 302)
html = c.get("/vehiculo/3").get_data(as_text=True)
if "--fx: 10%" not in html or "--fz: 2.0" not in html:
    fallas.append("el ajuste desde la ficha no se guardó")
fid = int(re.search(r"/archivo/(\d+)\" alt=\"Foto de", html).group(1))  # la foto anterior se reemplazó
esperar("foto desde la ficha pdf", c.post("/vehiculo/3/foto", content_type="multipart/form-data", data={
    "imagen_modo": "foto", "foto": (io.BytesIO(PDF), "x.pdf")}), 302)
esperar("volver al 3D", c.post("/vehiculo/3/editar", data={"imagen_modo": "3d"}), 302)
if "data-car3d" not in c.get("/vehiculo/3").get_data(as_text=True):
    fallas.append("no volvió el modelo 3D")
esperar("foto vuelve", c.post("/vehiculo/3/editar", data={"imagen_modo": "foto"}), 302)
if "car-photo" not in c.get("/vehiculo/3").get_data(as_text=True):
    fallas.append("la foto guardada no volvió")

# Libro: opciones de qué mostrar y compartido con foto
html = c.get("/vehiculo/3/libro").get_data(as_text=True)
for esperado in ('data-toggle="costos"', 'data-incluir', 'Qué se ve en el PDF'):
    if esperado not in html:
        fallas.append(f"falta en el libro: {esperado}")

# Cartel de recordatorios
if 'id="cartel"' not in c.get("/").get_data(as_text=True) or 'id="cartel"' not in c.get("/vehiculo/3").get_data(as_text=True):
    fallas.append("no aparece el cartel de recordatorios")

# Otra cuenta no ve ni toca nada de la primera
esperar("salir", c.post("/logout"), 302)
esperar("usuario repetido", c.post("/registro", data={"acepto": "1", "usuario": "JUAN", "clave": "clave-123", "clave2": "clave-123"}), 200)
esperar("registro ana", c.post("/registro", data={"acepto": "1", "usuario": "ana", "clave": "abcdefgh", "clave2": "abcdefgh"}), 302)
if "Focus" in c.get("/").get_data(as_text=True):
    fallas.append("ana ve los vehículos de juan")
for p in ("/vehiculo/1", "/vehiculo/3", "/vehiculo/3/editar", "/vehiculo/3/exportar",
          "/vehiculo/3/registro/nuevo", "/registro/1/editar"):
    esperar(f"ajeno {p}", c.get(p), 404)
esperar("borrar registro ajeno", c.post("/registro/1/eliminar"), 404)
esperar("borrar vehículo ajeno", c.post("/vehiculo/3/eliminar"), 404)
esperar("editar vehículo ajeno", c.post("/vehiculo/3/editar", data={"marca": "x"}), 404)
# Orden de la lista: se respeta y no se pueden tocar autos ajenos
ids_c = [int(x) for x in re.findall(r'data-id="(\d+)"', c.get("/").get_data(as_text=True))]
esperar("orden", c.post("/vehiculos/orden", data={"ids": ",".join(map(str, reversed(ids_c))) + ",9999"}), 204)
if [int(x) for x in re.findall(r'data-id="(\d+)"', c.get("/").get_data(as_text=True))] != ids_c[::-1]:
    fallas.append("no se guardó el orden de los vehículos")
esperar("foto ajena", c.get(f"/archivo/{fid}"), 404)
esperar("editar foto ajena", c.post("/vehiculo/3/foto", data={"imagen_modo": "3d"}), 404)
for p in ("/archivo/1", "/vehiculo/3/libro", "/vehiculo/3/compartir", "/vehiculo/3/documentos"):
    esperar(f"ajeno {p}", c.get(p), 404)
esperar("borrar archivo ajeno", c.post("/archivo/1/eliminar"), 404)
esperar("renovar ajeno", c.post("/documento/1/renovar"), 404)
esperar("subir a bóveda ajena", c.post("/vehiculo/3/boveda", data={}), 404)

# Link compartido: modo vista sin cuenta, sin documentación ni bóveda
c.post("/logout")
html = esperar("ver compartido", c.get(f"/c/{token}"), 200).get_data(as_text=True)
if "Modo vista" not in html or "Editar" in html:
    fallas.append("el compartido no está en modo vista")
for privado in ("La Segunda", "cedula.png", "Bóveda", "/registro/"):
    if privado in html:
        fallas.append(f"el compartido muestra algo privado: {privado}")
esperar("foto de registro compartida", c.get(f"/c/{token}/archivo/3"), 200)
esperar("foto del auto compartida", c.get(f"/c/{token}/archivo/{fid}"), 200)
esperar("bóveda no compartida", c.get(f"/c/{token}/archivo/1"), 404)
esperar("link inventado", c.get("/c/inventado"), 404)

# Ingreso: clave mala, buena y redirección segura
c.post("/logout")
esperar("clave mala", c.post("/login", data={"usuario": "juan", "clave": "mal"}), 200)
r = esperar("login ok", c.post("/login?next=//malo.com", data={"usuario": "Juan", "clave": "clave-123"}), 302)
if r.headers.get("Location") != "/":
    fallas.append(f"redirección insegura: {r.headers.get('Location')}")
esperar("ocultar adjuntos", c.post("/vehiculo/3/compartir", data={"accion": "opciones", "costos": "1"}), 302)
c2 = app.test_client()
esperar("foto oculta", c2.get(f"/c/{token}/archivo/3"), 404)
esperar("foto del auto sigue visible", c2.get(f"/c/{token}/archivo/{fid}"), 200)
esperar("dejar de compartir", c.post("/vehiculo/3/compartir", data={"accion": "desactivar"}), 302)
esperar("link anulado", c2.get(f"/c/{token}"), 404)
esperar("quitar adjunto", c.post("/registro/2/editar", data={"titulo": "Bujías", "quitar": "3"}), 302)
esperar("adjunto quitado", c.get("/archivo/3"), 404)
esperar("borrar de bóveda", c.post("/archivo/2/eliminar"), 302)
esperar("eliminar registro", c.post("/registro/1/eliminar"), 302)
esperar("eliminar vehículo", c.post("/vehiculo/2/eliminar"), 302)

# Estadísticas, privacidad, app instalable
# Actualizar el odómetro a mano: sube, no baja
esperar("km a mano", c.post("/vehiculo/3/km", data={"km": "987.654"}), 302)
if "987.654" not in c.get("/vehiculo/3").get_data(as_text=True).replace("&#39;", ""):
    fallas.append("el odómetro no muestra el km anotado a mano")
esperar("km que baja", c.post("/vehiculo/3/km", data={"km": "1.000"}), 302)
with sqlite3.connect(DB) as db:
    if db.execute("SELECT km_manual FROM vehiculos WHERE id = 3").fetchone()[0] != 987654:
        fallas.append("el odómetro bajó o no se guardó")
# Fechas: nada de año 0001, ni próximos controles en el pasado, ni trabajos en el futuro
with sqlite3.connect(DB) as db:
    antes = db.execute("SELECT COUNT(*) FROM registros WHERE vehiculo_id = 3").fetchone()[0]
for campos, esperado in (({"prox_fecha": "0001-01-01"}, None), ({"prox_fecha": "2020-05-01"}, None),
                         ({"prox_fecha": (date.today() + timedelta(days=30)).isoformat()}, "futuro"),
                         ({"fecha": "0001-01-01"}, "hoy"), ({"fecha": "2099-01-01"}, "hoy")):
    c.post("/vehiculo/3/registro/nuevo", data={"titulo": "prueba fechas", **campos})
with sqlite3.connect(DB) as db:
    filas = db.execute("SELECT fecha, prox_fecha FROM registros WHERE vehiculo_id = 3 AND titulo = 'prueba fechas' ORDER BY id").fetchall()
hoy = date.today().isoformat()
if [f[1] for f in filas][:2] != [None, None] or filas[2][1] is None or filas[3][0] != hoy or filas[4][0] != hoy:
    fallas.append(f"los límites de fecha no se aplican: {filas}")
with sqlite3.connect(DB) as db:
    db.execute("DELETE FROM registros WHERE titulo = 'prueba fechas'")
# Buscadores: robots, sitemap, Open Graph y noindex en lo privado
r = esperar("robots", app.test_client().get("/robots.txt"), 200)
if "Disallow: /" not in r.get_data(as_text=True) or "Sitemap:" not in r.get_data(as_text=True):
    fallas.append("robots.txt incompleto")
if "<loc>" not in esperar("sitemap", app.test_client().get("/sitemap.xml"), 200).get_data(as_text=True):
    fallas.append("sitemap.xml sin páginas")
anon = app.test_client().get("/")
if 'property="og:image"' not in anon.get_data(as_text=True) or 'name="description"' not in anon.get_data(as_text=True):
    fallas.append("faltan meta description u Open Graph en la portada")
if "noindex" in anon.headers.get("X-Robots-Tag", ""):
    fallas.append("la portada pública quedó como noindex")
if "noindex" not in c.get("/vehiculo/3").headers.get("X-Robots-Tag", ""):
    fallas.append("una página privada no tiene noindex")
esperar("og.png", app.test_client().get("/static/img/og.jpg"), 200)

# Contraseña: mínimo 8
esperar("clave de 7", app.test_client().post("/registro", data={"usuario": "corta7", "clave": "1234567", "clave2": "1234567", "acepto": "1"}), 200)

# Importar la copia exportada: se agregan los vehículos, registros y archivos a otra cuenta
r = c.get("/cuenta/exportar")
cimp = app.test_client()
cimp.post("/registro", data={"usuario": "importadora", "clave": "clave-123", "clave2": "clave-123", "acepto": "1"})
esperar("importar", cimp.post("/cuenta/importar", data={"copia": (io.BytesIO(r.data), "copia.zip")},
                                content_type="multipart/form-data"), 302)
html = cimp.get("/").get_data(as_text=True)
with sqlite3.connect(DB) as db:
    uid_imp = db.execute("SELECT id FROM usuarios WHERE usuario = 'importadora'").fetchone()[0]
    n_v = db.execute("SELECT COUNT(*) FROM vehiculos WHERE usuario_id = ?", (uid_imp,)).fetchone()[0]
    n_r = db.execute("SELECT COUNT(*) FROM registros r JOIN vehiculos v ON v.id = r.vehiculo_id WHERE v.usuario_id = ?", (uid_imp,)).fetchone()[0]
    n_a = db.execute("SELECT COUNT(*) FROM archivos a JOIN vehiculos v ON v.id = a.vehiculo_id WHERE v.usuario_id = ?", (uid_imp,)).fetchone()[0]
if not (n_v >= 1 and n_r >= 1 and n_a >= 1):
    fallas.append(f"la importación no trajo todo: {n_v} vehículos, {n_r} registros, {n_a} archivos")
for malo, nombre in ((b"no es un zip", "x.zip"), (b"", "vacio.zip")):
    esperar(f"importar {nombre}", cimp.post("/cuenta/importar", data={"copia": (io.BytesIO(malo), nombre)},
                                             content_type="multipart/form-data"), 302)
import zipfile as _zf  # noqa: E402
_b = io.BytesIO()
with _zf.ZipFile(_b, "w") as _z:
    _z.writestr("garajedata.json", '{"vehiculos": [{"nombre": "<script>alert(1)</script>", "usuario_id": 1, "id": 1, "share_token": "x", "anio": "mil", "registros": [{"titulo": "ok", "categoria": "rara", "costo": 1e999}]}]}')
esperar("importar raro", cimp.post("/cuenta/importar", data={"copia": (io.BytesIO(_b.getvalue()), "raro.zip")},
                                     content_type="multipart/form-data"), 302)
with sqlite3.connect(DB) as db:
    fila = db.execute("SELECT usuario_id, share_token, anio FROM vehiculos WHERE nombre LIKE '<script>%'").fetchone()
if not fila or fila[0] != uid_imp or fila[1] is not None or fila[2] is not None:
    fallas.append(f"la importación aceptó datos internos o mal tipados: {fila}")
if "<script>alert(1)" in cimp.get("/").get_data(as_text=True):
    fallas.append("XSS por importación")

# Consejo del día
html = c.get("/").get_data(as_text=True)
if 'id="consejo"' not in html or "Dato de garaje" not in html:
    fallas.append("no aparece el dato de garaje")
r = esperar("otro consejo", c.get("/consejo/3"), 200)
if not r.get_json().get("texto"):
    fallas.append("el consejo de /consejo/N viene vacío")
esperar("consejo enorme", c.get("/consejo/99999999999999999999"), 200)
# Calendario dentro de la página
html = esperar("calendario", c.get("/calendario"), 200).get_data(as_text=True)
if 'class="cal-grilla"' not in html or "noindex" not in c.get("/calendario").headers.get("X-Robots-Tag", ""):
    fallas.append("el calendario no muestra la grilla del mes")
for mes in ("2026-02", "1999-01", "2101-01", "2026-13", "abc", "9" * 30):
    esperar(f"calendario {mes}", c.get("/calendario?mes=" + mes), 200)
for q in ("a=1900&m=5", "a=9999&m=1", "a=2026&m=13", "a=2026&m=0", "a=abc&m=1", "a=2026&m=-1", "a=&m=", "a=2026&m=1x"):
    esperar(f"calendario {q}", c.get("/calendario?" + q), 200)
_hoy = date.today()
html = c.get(f"/calendario?a={_hoy.year - 50}&m=6").get_data(as_text=True)
if f'<option value="{_hoy.year - 2}" selected>' not in html or f'value="{_hoy.year - 3}"' in html or f'value="{_hoy.year + 6}"' in html:
    fallas.append("el calendario deja elegir años fuera de rango")
html = c.get(f"/calendario?a={_hoy.year + 50}&m=6").get_data(as_text=True)
if f'<option value="{_hoy.year + 5}" selected>' not in html or '<option value="12" selected>' not in html:
    fallas.append("el calendario no lleva un año muy lejano al último mes permitido")
esperar("calendario sin sesión", app.test_client().get("/calendario"), 302)
otra = app.test_client()
otra.post("/registro", data={"usuario": "sin-autos-cal", "clave": "clave-123", "clave2": "clave-123", "acepto": "1"})
html_otra = esperar("calendario de otra cuenta", otra.get("/calendario"), 200).get_data(as_text=True)
if "agenda-ev" in html_otra:
    fallas.append("el calendario muestra eventos de otra cuenta")
tanda = esperar("tanda de consejos", c.get("/consejos/5"), 200).get_json()
if len(tanda) != 40 or tanda[0]["salto"] != 5 or len({t["i"] for t in tanda}) != 40:
    fallas.append("la tanda de /consejos/N no trae 40 consejos distintos")
esperar("tanda enorme", c.get("/consejos/99999999999999999999"), 200)
import consejos  # noqa: E402
textos = [x[1] for x in consejos.CONSEJOS]
if len(set(textos)) != len(textos) or any(x[0] not in consejos.CATEGORIAS for x in consejos.CONSEJOS) or any(len(t) > 260 for t in textos):
    fallas.append("la lista de consejos tiene repetidos, categorías inválidas o textos muy largos")
vistos = {consejos.consejo_del_dia(date(2026, 1, 1) + timedelta(days=n))[0] for n in range(len(textos))}
if len(vistos) != len(textos):
    fallas.append("el consejo del día repite antes de recorrer todos")
# Ponderado por categoría: sin rachas y con apariciones parejas (cada categoría sale en proporción a sus consejos)
cats_orden = [consejos.CONSEJOS[i][0] for i in consejos.ordenados()]
if any(x == y for x, y in zip(cats_orden, cats_orden[1:])):
    fallas.append("el consejo del día repite la misma categoría dos días seguidos")
for cat in set(cats_orden):
    pos = [k for k, c in enumerate(cats_orden) if c == cat]
    esperado = len(cats_orden) / len(pos)
    if any(b - a > esperado * 2 or b - a < esperado / 3 for a, b in zip(pos, pos[1:])):
        fallas.append(f"las apariciones de la categoría {cat} no están repartidas parejo")
html = esperar("estadísticas", c.get("/vehiculo/3/estadisticas"), 200).get_data(as_text=True)
if "Gasto por mes" not in html or "Costo por km" not in html:
    fallas.append("faltan datos en estadísticas")
html = esperar("privacidad", c.get("/privacidad"), 200).get_data(as_text=True)
if "Política de Privacidad" not in html or "<b>" not in html or "Sin servicios externos" not in html:
    fallas.append("la política de privacidad no se muestra completa")
if "Términos y Condiciones de Uso" not in esperar("términos", c.get("/terminos"), 200).get_data(as_text=True):
    fallas.append("faltan los términos")
esperar("alta sin aceptar", app.test_client().post("/registro", data={"usuario": "sinacepto", "clave": "clave-123", "clave2": "clave-123"}), 200)
with sqlite3.connect(DB) as db:
    if db.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'sinacepto'").fetchone()[0]:
        fallas.append("se creó una cuenta sin aceptar los términos")
esperar("manifest", c.get("/static/manifest.webmanifest"), 200)

# Descargar todos mis datos
import json  # noqa: E402
import zipfile  # noqa: E402
r = esperar("exportar todo", c.get("/cuenta/exportar"), 200)
with zipfile.ZipFile(io.BytesIO(r.data)) as z:
    nombres = z.namelist()
    datos = json.loads(z.read("garajedata.json"))
if not any(n.endswith("registros.csv") for n in nombres) or not any("/archivos/" in n for n in nombres):
    fallas.append(f"al zip le falta algo: {nombres}")
if sorted(v["id"] for v in datos["vehiculos"]) != [1, 3] or "share_token" in datos["vehiculos"][0]:
    fallas.append(f"el zip trae vehículos ajenos o datos internos: {[v['id'] for v in datos['vehiculos']]}")

# Calendario de avisos
esperar("crear calendario", c.post("/cuenta/calendario", data={}), 302)
cal = re.search(r'id="cal-link">[^<]*/cal/([^<]+)\.ics<', c.get("/cuenta").get_data(as_text=True)).group(1)
ics = esperar("ver calendario", app.test_client().get(f"/cal/{cal}.ics"), 200).get_data(as_text=True)
if "BEGIN:VCALENDAR" not in ics or "BEGIN:VEVENT" not in ics:
    fallas.append("el calendario no tiene eventos")
esperar("calendario inventado", c.get("/cal/inventadoinventadoinventado.ics"), 404)
esperar("quitar calendario", c.post("/cuenta/calendario", data={"accion": "quitar"}), 302)
esperar("calendario anulado", c.get(f"/cal/{cal}.ics"), 404)

# Transferencia: juan genera el código (más abajo lo recibe pepe)
esperar("transferir form", c.get("/vehiculo/3/transferir"), 200)
html = esperar("generar transferencia", c.post("/vehiculo/3/transferir", data={}), 200).get_data(as_text=True)
cod_transfer = re.search(r'id="codigo-transfer">([A-Z0-9-]+)<', html).group(1)

# Código de recuperación: se ve una sola vez, sirve una vez y cambia la contraseña

c.post("/logout")
c.post("/registro", data={"acepto": "1", "usuario": "pepe", "clave": "clave-123", "clave2": "clave-123"})
html = esperar("ver código", c.get("/cuenta/codigo"), 200).get_data(as_text=True)
codigo = re.search(r'id="codigo">([A-Z0-9-]+)<', html).group(1)
esperar("código ya mostrado", c.get("/cuenta/codigo"), 302)
esperar("mi cuenta", c.get("/cuenta"), 200)
c.post("/logout")
esperar("recuperar form", c.get("/recuperar"), 200)
esperar("código malo", c.post("/recuperar", data={"usuario": "pepe", "codigo": "AAAA-BBBB-CCCC-DDDD",
                                                  "clave": "nueva-123", "clave2": "nueva-123"}), 200)
esperar("recuperar ok", c.post("/recuperar", data={"usuario": "PEPE", "codigo": codigo.lower().replace("-", " "),
                                                   "clave": "nueva-123", "clave2": "nueva-123"}), 302)
c.post("/logout")
esperar("código usado no sirve", c.post("/recuperar", data={"usuario": "pepe", "codigo": codigo,
                                                            "clave": "otra-1234", "clave2": "otra-1234"}), 200)
esperar("clave vieja no entra", c.post("/login", data={"usuario": "pepe", "clave": "clave-123"}), 200)
esperar("clave nueva entra", c.post("/login", data={"usuario": "pepe", "clave": "nueva-123"}), 302)
esperar("cambiar clave mal", c.post("/cuenta", data={"accion": "clave", "actual": "x", "clave": "abcdefgh",
                                                     "clave2": "abcdefgh"}), 200)
esperar("cambiar clave", c.post("/cuenta", data={"accion": "clave", "actual": "nueva-123", "clave": "abcdefgh",
                                                 "clave2": "abcdefgh"}), 302)
esperar("generar código", c.post("/cuenta", data={"accion": "codigo", "actual": "abcdefgh"}), 302)

# pepe recibe el auto de juan con el código de transferencia
esperar("recibir form", c.get("/recibir"), 200)
esperar("código de transferencia malo", c.post("/recibir", data={"codigo": "AAAA-BBBB-CCCC"}), 200)
esperar("recibir auto", c.post("/recibir", data={"codigo": cod_transfer.lower()}), 302)
esperar("auto recibido", c.get("/vehiculo/3"), 200)
esperar("código usado", c.post("/recibir", data={"codigo": cod_transfer}), 200)

# Borrar la cuenta: pide el usuario escrito y la contraseña; se lleva todo
esperar("borrar cuenta sin confirmar", c.post("/cuenta", data={"accion": "borrar", "confirmar": "x", "actual": "abcdefgh"}), 200)
esperar("borrar cuenta", c.post("/cuenta", data={"accion": "borrar", "confirmar": "Pepe", "actual": "abcdefgh"}), 302)
esperar("cuenta borrada", c.post("/login", data={"usuario": "pepe", "clave": "abcdefgh"}), 200)
with sqlite3.connect(DB) as db:
    if db.execute("SELECT COUNT(*) FROM vehiculos WHERE id = 3").fetchone()[0]:
        fallas.append("borrar la cuenta no borró sus vehículos")

# Bloqueo tras muchos intentos
c.post("/logout")
for _ in range(5):
    c.post("/login", data={"usuario": "ana", "clave": "mal"})
esperar("bloqueo", c.post("/login", data={"usuario": "ana", "clave": "abcdefgh"}), 429)

# CSRF: sin el token el formulario se rechaza; con el token de la página, pasa.
app.config["CSRF_APAGADO"] = False
c3 = app.test_client()
esperar("registro sin token", c3.post("/registro", data={"acepto": "1", "usuario": "csrf_x", "clave": "clave1234", "clave2": "clave1234"}), 400)
tok = re.search(r'name="csrf" value="([^"]+)"', c3.get("/registro").get_data(as_text=True)).group(1)
esperar("registro con token", c3.post("/registro", data={"acepto": "1", "csrf": tok, "usuario": "csrf_x", "clave": "clave1234", "clave2": "clave1234"}), 302)
tok = re.search(r'<meta name="csrf" content="([^"]+)"', c3.get("/").get_data(as_text=True)).group(1)
esperar("orden con encabezado", c3.post("/vehiculos/orden", data={"ids": ""}, headers={"X-CSRF-Token": tok}), 204)
app.config["CSRF_APAGADO"] = True

# Límite de cuentas nuevas por IP
nucleo.ALTAS_IP.clear()
nucleo.MAX_ALTAS_IP = 1
c4 = app.test_client()
esperar("alta 1 de la IP", c4.post("/registro", data={"acepto": "1", "usuario": "ip_uno", "clave": "clave-123", "clave2": "clave-123"}), 302)
c4.post("/logout")
esperar("alta 2 de la IP bloqueada", c4.post("/registro", data={"acepto": "1", "usuario": "ip_dos", "clave": "clave-123", "clave2": "clave-123"}), 429)
nucleo.MAX_ALTAS_IP = 100

print("\n".join(fallas) if fallas else "TODO OK")
sys.exit(1 if fallas else 0)
