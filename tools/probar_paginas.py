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

# Versión de equipamiento: se guarda aparte de la generación y aparece en el nombre
esperar("alta con versión", c.post("/vehiculo/nuevo", data={
    "marca": "chevrolet", "modelo": "cruze 5", "version": "J400 (2ª gen.)", "equipamiento": "LTZ", "carroceria": "hatchback"}), 302)
with sqlite3.connect(DB) as db:
    vid_eq = db.execute("SELECT id, equipamiento, version FROM vehiculos WHERE modelo = 'Cruze 5' ORDER BY id DESC").fetchone()
if not vid_eq or vid_eq[1:] != ("LTZ", "J400 (2ª gen.)"):
    fallas.append(f"la versión de equipamiento no se guardó aparte: {vid_eq}")
elif "Chevrolet Cruze 5 J400 (2ª gen.) LTZ" not in c.get(f"/vehiculo/{vid_eq[0]}").get_data(as_text=True):
    fallas.append("la versión de equipamiento no aparece en el nombre del auto")
if '"equipamientos"' not in c.get("/vehiculo/nuevo").get_data(as_text=True) or 'id="combo-equipamiento"' not in c.get("/vehiculo/nuevo").get_data(as_text=True):
    fallas.append("el formulario no ofrece las versiones de equipamiento")
# Un dato viejo con la versión en el campo de generación («Ghia») pasa solo al campo nuevo; «MK1» se queda.
with sqlite3.connect(DB) as db:
    viejo = db.execute("INSERT INTO vehiculos (usuario_id, nombre, marca, modelo, version) VALUES (1, '', 'Ford', 'Focus', 'ghia')").lastrowid
    gen = db.execute("INSERT INTO vehiculos (usuario_id, nombre, marca, modelo, version) VALUES (1, '', 'Ford', 'Focus', 'MK1')").lastrowid
nucleo.init_db()
with sqlite3.connect(DB) as db:
    if db.execute("SELECT equipamiento, version FROM vehiculos WHERE id = ?", (viejo,)).fetchone() != ("Ghia", None):
        fallas.append("la versión vieja «Ghia» no pasó al campo nuevo")
    if db.execute("SELECT equipamiento, version FROM vehiculos WHERE id = ?", (gen,)).fetchone() != (None, "MK1"):
        fallas.append("la generación «MK1» se movió por error")
    db.execute("DELETE FROM vehiculos WHERE id IN (?, ?, ?)", (viejo, gen, vid_eq[0] if vid_eq else -1))

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
faltante = (date.today() - timedelta(days=40)).isoformat()
esperar("guardar documentos", c.post("/vehiculo/3/documentos", data={
    "vence_vtv": faltante, "cada_vtv": "1", "vence_seguro_pago": (date.today() + timedelta(days=200)).isoformat(), "cada_seguro_pago": "1",
    "detalle_seguro": "La Segunda"}), 302)
html = c.get("/vehiculo/3").get_data(as_text=True)
if "Venció hace" not in html or "La Segunda" not in html:
    fallas.append("no se ven los vencimientos")
# Una fecha inválida avisa y no toca nada (antes se descartaba en silencio y hasta borraba el vencimiento).
r = esperar("documentos con fecha mala", c.post("/vehiculo/3/documentos", data={
    "vence_vtv": "fecha mala", "cada_vtv": "1", "detalle_vtv": "planta"}), 200)
if "no es válida" not in r.get_data(as_text=True):
    fallas.append("no avisa cuando la fecha de un vencimiento es inválida")
with sqlite3.connect(DB) as db:
    if db.execute("SELECT vence FROM documentos WHERE vehiculo_id = 3 AND tipo = 'vtv'").fetchone()[0] != faltante:
        fallas.append("una fecha inválida borró o cambió el vencimiento guardado")
# Una fecha vieja (vencida hace años) sí se puede cargar y queda como vencida.
esperar("documentos con fecha vieja", c.post("/vehiculo/3/documentos", data={
    "vence_matafuego": "2020-05-01", "cada_matafuego": "12"}), 302)
with sqlite3.connect(DB) as db:
    if db.execute("SELECT vence FROM documentos WHERE vehiculo_id = 3 AND tipo = 'matafuego'").fetchone()[0] != "2020-05-01":
        fallas.append("no se pudo cargar un vencimiento viejo")
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
if 'id="atencion-titulo"' not in c.get("/").get_data(as_text=True) or 'id="cartel"' not in c.get("/vehiculo/3").get_data(as_text=True):
    fallas.append("no aparece el resumen de atención o el cartel del perfil")

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
# Un kilometraje imposible se avisa y no se guarda (tampoco puede romper las páginas).
esperar("km imposible", c.post("/vehiculo/3/km", data={"km": "999999999999"}), 302)
if "no parece real" not in c.get("/vehiculo/3").get_data(as_text=True):
    fallas.append("no avisa de un kilometraje imposible")
with sqlite3.connect(DB) as db:
    if db.execute("SELECT km_manual FROM vehiculos WHERE id = 3").fetchone()[0] != 987654:
        fallas.append("guardó un kilometraje imposible")
# Un año imposible tampoco: se vuelve a mostrar el formulario y no se toca la base.
r = esperar("editar con año imposible", c.post("/vehiculo/3/editar", data={
    "marca": "Ford", "modelo": "Focus", "anio": "999999", "km_inicial": "129.500"}), 200)
if "año tiene que estar" not in r.get_data(as_text=True):
    fallas.append("no avisa de un año imposible")
with sqlite3.connect(DB) as db:
    if db.execute("SELECT anio FROM vehiculos WHERE id = 3").fetchone()[0] is not None:
        fallas.append("guardó un año imposible")
for p in ("/", "/vehiculo/3", "/calendario"):
    esperar(f"página sana después de datos raros {p}", c.get(p), 200)
# Fechas inválidas se rechazan; los próximos controles históricos se pueden conservar.
with sqlite3.connect(DB) as db:
    antes = db.execute("SELECT COUNT(*) FROM registros WHERE vehiculo_id = 3").fetchone()[0]
for campos, codigo in (({"prox_fecha": "0001-01-01"}, 200), ({"prox_fecha": "2020-05-01"}, 302),
                       ({"prox_fecha": (date.today() + timedelta(days=30)).isoformat()}, 302),
                       ({"fecha": "0001-01-01"}, 200), ({"fecha": "2099-01-01"}, 200)):
    esperar("validación de fechas", c.post("/vehiculo/3/registro/nuevo", data={"titulo": "prueba fechas", **campos}), codigo)
with sqlite3.connect(DB) as db:
    filas = db.execute("SELECT fecha, prox_fecha FROM registros WHERE vehiculo_id = 3 AND titulo = 'prueba fechas' ORDER BY id").fetchall()
hoy = date.today().isoformat()
if filas != [(hoy, "2020-05-01"), (hoy, (date.today() + timedelta(days=30)).isoformat())]:
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

# Foto de perfil: se sube recortada, la ve solo su dueño, se rechazan PDF y basura, y se borra al quitarla
from PIL import Image as _Img  # noqa: E402
import archivos  # noqa: E402
_b = io.BytesIO()
_Img.new("RGB", (900, 600), (200, 30, 30)).save(_b, "PNG")
cfoto = app.test_client()
cfoto.post("/registro", data={"usuario": "confoto", "clave": "clave-123", "clave2": "clave-123", "acepto": "1"})
esperar("subir foto de perfil", cfoto.post("/cuenta/foto", data={"foto": (io.BytesIO(_b.getvalue()), "yo.png")},
                                           content_type="multipart/form-data"), 302)
with sqlite3.connect(DB) as db:
    foto_disco = db.execute("SELECT foto FROM usuarios WHERE usuario = 'confoto'").fetchone()[0]
r = esperar("ver foto de perfil", cfoto.get("/cuenta/foto"), 200)
if r.mimetype != "image/jpeg" or _Img.open(io.BytesIO(r.data)).size != (320, 320):
    fallas.append("la foto de perfil no quedó cuadrada de 320 px en JPEG")
r.close()  # en Windows un archivo abierto no se puede borrar
if "/cuenta/foto?v=" not in cfoto.get("/").get_data(as_text=True):
    fallas.append("la foto de perfil no aparece en la barra")
esperar("foto de perfil sin sesión", app.test_client().get("/cuenta/foto"), 302)
esperar("foto de perfil de otro (sin foto propia)", c.get("/cuenta/foto"), 404)
for malo, nombre in ((b"%PDF-1.4 hola", "x.pdf"), (b"no es imagen", "x.jpg"), (b"", "vacio.png")):
    cfoto.post("/cuenta/foto", data={"foto": (io.BytesIO(malo), nombre)}, content_type="multipart/form-data")
with sqlite3.connect(DB) as db:
    if db.execute("SELECT foto FROM usuarios WHERE usuario = 'confoto'").fetchone()[0] != foto_disco:
        fallas.append("un archivo inválido reemplazó la foto de perfil")
esperar("quitar foto de perfil", cfoto.post("/cuenta/foto", data={"accion": "quitar"}), 302)
if os.path.exists(archivos.ruta(foto_disco)):
    fallas.append("al quitar la foto de perfil el archivo quedó en el disco")
cfoto.post("/cuenta/foto", data={"foto": (io.BytesIO(_b.getvalue()), "yo.png")}, content_type="multipart/form-data")
with sqlite3.connect(DB) as db:
    foto_disco = db.execute("SELECT foto FROM usuarios WHERE usuario = 'confoto'").fetchone()[0]
cfoto.post("/cuenta", data={"accion": "borrar", "actual": "clave-123", "confirmar": "confoto"})
if os.path.exists(archivos.ruta(foto_disco)):
    fallas.append("al borrar la cuenta la foto de perfil quedó en el disco")

# Pendientes («Lo tengo que hacer»): se anotan a futuro, aparecen en la ficha y el calendario,
# no se pueden tocar desde otra cuenta y se cierran al registrar que se hicieron.
from datetime import timedelta as _td  # noqa: E402
_enero = (date.today() + _td(days=90)).isoformat()
esperar("pendiente sin fecha ni km", c.post("/vehiculo/3/registro/nuevo", data={"modo": "pendiente", "titulo": "Aceite"}), 200)
r = esperar("pendiente con fecha pasada", c.post("/vehiculo/3/registro/nuevo", data={
    "modo": "pendiente", "titulo": "Aceite", "pend_fecha": "2000-01-01", "pend_km": "150.000"}), 200)
if "tiene que ser de hoy en adelante" not in r.get_data(as_text=True):
    fallas.append("un pendiente con fecha pasada no avisa el motivo")
esperar("pendiente", c.post("/vehiculo/3/registro/nuevo", data={
    "modo": "pendiente", "titulo": "Cambio de aceite (pendiente)", "categoria": "fluidos", "pend_fecha": _enero,
    "fecha": "2099-01-01", "costo": "999"}), 302)
with sqlite3.connect(DB) as db:
    pend = db.execute("SELECT id, fecha, categoria FROM pendientes WHERE titulo = 'Cambio de aceite (pendiente)'").fetchone()
    n_regs_antes = db.execute("SELECT COUNT(*) FROM registros WHERE vehiculo_id = 3").fetchone()[0]
if not pend or pend[1:] != (_enero, "fluidos"):
    fallas.append(f"el pendiente no se guardó bien: {pend}")
else:
    if "Cambio de aceite (pendiente)" not in c.get("/vehiculo/3").get_data(as_text=True):
        fallas.append("el pendiente no aparece en la ficha")
    mes = _enero[:7]
    if "Cambio de aceite (pendiente)" not in c.get(f"/calendario?mes={mes}").get_data(as_text=True):
        fallas.append("el pendiente no aparece en el calendario")
    otra_p = app.test_client()
    otra_p.post("/registro", data={"usuario": "ajena-pend", "clave": "clave-123", "clave2": "clave-123", "acepto": "1"})
    esperar("«ya lo hice» de otra cuenta", otra_p.post(f"/pendiente/{pend[0]}/hecho"), 404)
    esperar("borrar pendiente de otra cuenta", otra_p.post(f"/pendiente/{pend[0]}/borrar"), 404)
    html = esperar("ya lo hice", c.post(f"/pendiente/{pend[0]}/hecho"), 200).get_data(as_text=True)
    if f'name="pendiente" value="{pend[0]}"' not in html or "Cambio de aceite (pendiente)" not in html:
        fallas.append("«Ya lo hice» no abre el registro con los datos del pendiente")
    esperar("registrar el pendiente hecho", c.post("/vehiculo/3/registro/nuevo", data={
        "titulo": "Cambio de aceite (pendiente)", "categoria": "fluidos", "fecha": date.today().isoformat(),
        "costo": "50.000", "pendiente": str(pend[0])}), 302)
    with sqlite3.connect(DB) as db:
        if db.execute("SELECT 1 FROM pendientes WHERE id = ?", (pend[0],)).fetchone():
            fallas.append("el pendiente no se cerró al registrarlo")
        if db.execute("SELECT COUNT(*) FROM registros WHERE vehiculo_id = 3").fetchone()[0] != n_regs_antes + 1:
            fallas.append("al cerrar el pendiente no quedó el registro en la bitácora")
c.post("/vehiculo/3/registro/nuevo", data={"modo": "pendiente", "titulo": "Rotar cubiertas", "pend_km": "999.999"})
with sqlite3.connect(DB) as db:
    pid2 = db.execute("SELECT id FROM pendientes WHERE titulo = 'Rotar cubiertas'").fetchone()
if not pid2:
    fallas.append("no se pudo anotar un pendiente solo por kilometraje")
else:
    esperar("borrar pendiente", c.post(f"/pendiente/{pid2[0]}/borrar"), 302)
    with sqlite3.connect(DB) as db:
        if db.execute("SELECT 1 FROM pendientes WHERE id = ?", (pid2[0],)).fetchone():
            fallas.append("el pendiente no se borró")
esperar("pendiente inexistente", c.post("/pendiente/999999/hecho"), 404)

# Panel de administración: 404 para cualquiera que no sea admin; el admin ve números y cuentas, sin contenido
esperar("admin sin sesión", app.test_client().get("/admin"), 404)
esperar("admin sin rango", c.get("/admin"), 404)
import subprocess  # noqa: E402
cadm = app.test_client()
cadm.post("/registro", data={"usuario": "jefa", "clave": "clave-123", "clave2": "clave-123", "acepto": "1"})
salida = subprocess.run([sys.executable, os.path.join(RAIZ, "tools", "admin.py"), "jefa"], capture_output=True, text=True,
                        env={**os.environ, "DB_PATH": DB}).stdout
if "ahora es administrador" not in salida:
    fallas.append(f"tools/admin.py no dio el rango: {salida!r}")
html = esperar("admin con rango", cadm.get("/admin"), 200).get_data(as_text=True)
if "Panel de control" not in html or "jefa" not in html or "noindex" not in cadm.get("/admin").headers.get("X-Robots-Tag", ""):
    fallas.append("el panel de administración no muestra las cuentas o se puede indexar")
if "AA 123 BC" in html or "Cambio de aceite" in html:
    fallas.append("el panel de administración muestra contenido privado de los vehículos")
if 'href="/admin"' not in cadm.get("/cuenta").get_data(as_text=True) or 'href="/admin"' in c.get("/cuenta").get_data(as_text=True):
    fallas.append("el acceso al panel aparece donde no debe (o no aparece para el admin)")
with sqlite3.connect(DB) as db:
    if db.execute("SELECT actividad FROM usuarios WHERE usuario = 'jefa'").fetchone()[0] != date.today().isoformat():
        fallas.append("no se anota la última actividad de la cuenta")
subprocess.run([sys.executable, os.path.join(RAIZ, "tools", "admin.py"), "jefa", "--quitar"], capture_output=True,
               env={**os.environ, "DB_PATH": DB})
esperar("admin quitado", cadm.get("/admin"), 404)

# Créditos en su propia página (pública), enlazada desde el pie; el pie ya no lista los modelos
r = esperar("créditos", app.test_client().get("/creditos"), 200).get_data(as_text=True)
if "Comrade1280" not in r or "car-logos-dataset" not in r or "Open Font License" not in r:
    fallas.append("a la página de créditos le falta alguna fuente")
pie = app.test_client().get("/terminos").get_data(as_text=True)
if 'href="/creditos"' not in pie or "Modelos 3D:" in pie:
    fallas.append("el pie no enlaza a Créditos o sigue mostrando los modelos")
# Botón flotante: la página marca su botón principal y el flotante arranca oculto
html = c.get("/vehiculo/3").get_data(as_text=True)
if "data-registro-principal" not in html or "carga-flotante carga-oculta" not in html:
    fallas.append("el botón flotante no sabe cuál es el botón principal de la ficha")

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
# Preferencia de datos de garaje: Mi cuenta → Preferencias filtra consejos, «Otro» y el del día
tok = re.search(r'name="csrf" value="([^"]+)"', c.get("/cuenta").get_data(as_text=True)).group(1)
app.config["CSRF_APAGADO"] = False
esperar("preferencia sin csrf", c.post("/cuenta/datos-garaje", data={"datos": "sin_moto"}), 400)
app.config["CSRF_APAGADO"] = True
esperar("preferencia inválida", c.post("/cuenta/datos-garaje", data={"csrf": tok, "datos": "todo-mal"}), 302)
for pref, cumple in (("sin_moto", lambda k: k != "motos"), ("sin_auto", lambda k: k == "motos")):
    esperar("guardar " + pref, c.post("/cuenta/datos-garaje", data={"csrf": tok, "datos": pref}), 302)
    tanda_p = c.get("/consejos/5").get_json()
    if len(tanda_p) != 40 or len({t["i"] for t in tanda_p}) != 40 or not all(cumple(t["clave"]) for t in tanda_p):
        fallas.append(f"la preferencia {pref} deja pasar consejos ocultos en /consejos")
    if not all(cumple(c.get(f"/consejo/{n}").get_json()["clave"]) for n in range(0, 30)):
        fallas.append(f"la preferencia {pref} deja pasar consejos ocultos en /consejo/N")
    html_p = c.get("/").get_data(as_text=True)
    if f'value="{pref}" checked' not in c.get("/cuenta").get_data(as_text=True):
        fallas.append(f"Mi cuenta no marca la preferencia {pref}")
    if pref == "sin_auto" and 'class="consejo consejo-motos"' not in html_p:
        fallas.append("con «Ocultar los de auto» no aparece un dato de moto en el inicio")
    if pref == "sin_moto" and 'class="consejo consejo-motos"' in html_p:
        fallas.append("con «Ocultar los de moto» aparece un dato de moto en el inicio")
esperar("preferencia vuelta a todos", c.post("/cuenta/datos-garaje", data={"csrf": tok, "datos": "todos"}), 302)
if len(c.get("/consejos/5").get_json()) != 40:
    fallas.append("al volver a «Todos» no se recuperan los consejos")
import consejos  # noqa: E402
textos = [x[1] for x in consejos.CONSEJOS]
if len(consejos.DATOS_MOTO) != 100 or sum(cat == "motos" for cat, _ in consejos.CONSEJOS) != 100:
    fallas.append("deben existir exactamente 100 datos de motos")
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
if "Gasto por mes" not in html or "Costo registrado por km" not in html:
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
esperar("enlace anterior abre registro", c.get("/cargar?vid=3"), 302)
esperar("selector rechaza auto ajeno", c.get("/registro/nuevo?vid=1"), 404)
esperar("carga rápida retirada", c.post("/cargar", data={"vid":"3", "tipo":"combustible"}), 405)
esperar("registro único", c.get("/vehiculo/3/registro/nuevo"), 200)
html = c.get('/vehiculo/3/registro/nuevo').get_data(as_text=True)
if 'Chapa y pintura' not in html or 'Neumáticos' not in html or 'Accesorios' not in html or 'value="modificacion"' in html:
    fallas.append('las categorías del formulario único no están reorganizadas')
if not html.index('Gastos y papeles') < html.index('value="combustible"'):
    fallas.append('combustible debe pertenecer a gastos y papeles')
for tipo in ('combustible','seguro','patente','vtv','estacionamiento','lavado','accesorios','multas','tramites','neumaticos','chapa'):
    esperar('registro '+tipo, c.post('/vehiculo/3/registro/nuevo', data={'titulo':'Prueba '+tipo,'categoria':tipo,'costo':'1.200,50','fecha':date.today().isoformat()}), 302)
    with sqlite3.connect(DB) as db:
        dato = db.execute('SELECT categoria,costo FROM registros WHERE vehiculo_id=3 ORDER BY id DESC LIMIT 1').fetchone()
        if dato != (tipo,1200.5):
            fallas.append('la categoría '+tipo+' no se conserva al guardar')
    if '1.200,50' not in c.get('/vehiculo/3?cat='+tipo).get_data(as_text=True):
        fallas.append('el filtro no incluye el gasto de '+tipo)
# Las categorías antiguas se fusionan sin borrar contenido, y la migración es repetible.
with sqlite3.connect(DB) as db:
    antiguo = db.execute("INSERT INTO registros (vehiculo_id,fecha,categoria,titulo,costo) VALUES (3,?,'modificacion','Polarizado anterior',1234)", (date.today().isoformat(),)).lastrowid
    peaje = db.execute("INSERT INTO registros (vehiculo_id,fecha,categoria,titulo,costo) VALUES (3,?,'peajes','Peaje ruta 2',900)", (date.today().isoformat(),)).lastrowid
nucleo.init_db()
nucleo.init_db()
with sqlite3.connect(DB) as db:
    if db.execute('SELECT categoria,titulo,costo FROM registros WHERE id=?',(antiguo,)).fetchone() != ('accesorios','Polarizado anterior',1234):
        fallas.append('la fusión de categorías alteró el registro anterior')
    if db.execute('SELECT categoria,titulo,costo FROM registros WHERE id=?',(peaje,)).fetchone() != ('estacionamiento','Peaje ruta 2',900):
        fallas.append('los peajes viejos no pasaron a «Cochera y peajes»')
# Una categoría vieja enviada por el formulario se guarda en la nueva; una inventada, en «Otro».
for enviada, guardada in (('peajes', 'estacionamiento'), ('modificacion', 'accesorios'), ('<script>', 'otro')):
    c.post('/vehiculo/3/registro/nuevo', data={'titulo': 'Cat ' + enviada, 'categoria': enviada, 'fecha': date.today().isoformat()})
    with sqlite3.connect(DB) as db:
        if db.execute('SELECT categoria FROM registros WHERE vehiculo_id=3 ORDER BY id DESC LIMIT 1').fetchone()[0] != guardada:
            fallas.append(f'la categoría enviada {enviada} no se guardó como {guardada}')
html = c.get('/vehiculo/3/registro/nuevo').get_data(as_text=True)
if html.count('class="cat-option') != 16 or 'value="peajes"' in html or 'Lo que no entra arriba' not in html:
    fallas.append('el formulario no muestra las 16 categorías ordenadas con su ayuda')
html = c.get('/vehiculo/3/estadisticas').get_data(as_text=True)
if 'Chapa y pintura' not in html or 'Neumáticos' not in html or 'Accesorios' not in html:
    fallas.append('las categorías nuevas no aparecen en gastos')

from rutas.estadisticas import resumen_gastos
v_gastos = {"km_manual":None,"km_manual_fecha":None}
datos = [dict(fecha='2026-09-15',km=1000,costo=10), dict(fecha='2026-09-30',km=None,costo=500),
         dict(fecha='2026-10-01',km=1100,costo=0), dict(fecha='2026-10-10',km=1200,costo=20),
         dict(fecha='2026-10-12',km=None,costo=None), dict(fecha='2026-10-20',km=1300,costo=999)]
res = resumen_gastos(datos,v_gastos,date(2026,10,15))
if res['mes_previo'] != 10 or res['mes_actual'] != 20 or res['diferencia'] != 100 or res['sin_costo'] != 1 or res['costo_km'] != 2.6:
    fallas.append("el resumen mezcla períodos, gastos futuros o lecturas sin fecha")
res = resumen_gastos([dict(fecha='2026-10-01',km=0,costo=None),dict(fecha='2026-10-02',km=100,costo=0)],v_gastos,date(2026,10,15))
if res['costo_km'] != 0:
    fallas.append("el costo por km pierde los trabajos gratuitos o la lectura cero")
res = resumen_gastos([dict(fecha='2026-10-01',km=100,costo=20)],v_gastos,date(2026,10,15))
if res['costo_km'] is not None:
    fallas.append("el costo por km inventa distancia con una sola lectura")
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
esperar("registro sin token", c3.post("/vehiculo/3/registro/nuevo", data={"titulo":"Prueba", "categoria":"combustible"}), 400)
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
