"""Auditoría: ataca la app (en local, con una base temporal) para encontrar fallas de seguridad y cosas que se rompen.

Uso:  python tools/auditoria.py
Imprime cada hallazgo como [SEGURIDAD] o [ROMPE] y termina con el resumen. Código de salida 1 si hay hallazgos.
No toca bitacora.db ni el sitio publicado.
"""
import io
import os
import re
import sqlite3
import struct
import sys
import tempfile
import threading
import time
import zlib

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
DB = os.path.join(tempfile.mkdtemp(), "auditoria.db")
os.environ["DB_PATH"] = DB
os.environ["UPLOAD_DIR"] = os.path.join(os.path.dirname(DB), "uploads")
os.environ["RESPALDOS_DIR"] = os.path.join(os.path.dirname(DB), "respaldos")
os.environ["GARAJEDATA_HTTPS"] = "1"  # se audita como en el sitio publicado (cookie Secure, HSTS)

from app import app  # noqa: E402
import nucleo  # noqa: E402

nucleo.MAX_ALTAS_IP = 10_000
app.config["PROPAGATE_EXCEPTIONS"] = False  # que un error 500 se vea como 500, no como excepción
hallazgos = []


def hallazgo(tipo, texto):
    hallazgos.append((tipo, texto))
    print(f"[{tipo}] {texto}")


def pixel_png(w, h):
    """PNG válido de w×h (todo negro) sin armar la imagen en memoria: sirve para probar bombas."""
    def trozo(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    fila = b"\x00" + b"\x00" * w
    comp = zlib.compressobj(9)
    datos = b"".join(comp.compress(fila) for _ in range(h)) + comp.flush()
    return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + trozo(b"IDAT", datos) + trozo(b"IEND", b""))


PNG_OK = pixel_png(8, 8)
PDF_OK = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def token_de(cliente, ruta="/registro"):
    html = cliente.get(ruta).get_data(as_text=True)
    m = re.search(r'name="csrf" value="([^"]+)"', html) or re.search(r'<meta name="csrf" content="([^"]+)"', html)
    return m.group(1) if m else ""


class Sesion:
    """Cliente con CSRF real (como un navegador)."""

    def __init__(self, usuario=None):
        self.c = app.test_client()
        self.usuario = usuario
        if usuario:
            r = self.post("/registro", {"usuario": usuario, "clave": "clave-larga-1", "clave2": "clave-larga-1", "acepto": "1"},
                          ruta_token="/registro")
            assert r.status_code == 302, f"no se pudo crear {usuario}: {r.status_code}"

    def get(self, ruta, **kw):
        return self.c.get(ruta, **kw)

    def post(self, ruta, datos=None, ruta_token=None, **kw):
        datos = dict(datos or {})
        if "csrf" not in datos and "headers" not in kw:
            datos["csrf"] = token_de(self.c, ruta_token or "/cuenta" if self.usuario else "/registro")
        return self.c.post(ruta, data=datos, **kw)


# ============================================================================ preparación
ana = Sesion("ana_auditoria")
bob = Sesion("bob_auditoria")
atacante = app.test_client()

r = ana.post("/vehiculo/nuevo", {"marca": "Ford", "modelo": "Focus", "nombre": "Auto de Ana", "patente": "AB123CD",
                                 "km_inicial": "1000", "uso": "promedio", "calcular_uso": "1"})
assert r.status_code == 302, r.status_code
with sqlite3.connect(DB) as db:
    VID_ANA = db.execute("SELECT id FROM vehiculos WHERE nombre = 'Auto de Ana'").fetchone()[0]
r = ana.post(f"/vehiculo/{VID_ANA}/registro/nuevo", {"titulo": "Aceite", "fecha": "2026-01-10", "km": "5000", "costo": "1000",
                                                       "categoria": "fluidos", "prox_km": "15000"})
assert r.status_code == 302
r = ana.post(f"/vehiculo/{VID_ANA}/boveda", {"categoria": "cedula", "archivos": (io.BytesIO(PNG_OK), "cedula.png")},
             headers={"X-CSRF-Token": token_de(ana.c, "/cuenta")}, content_type="multipart/form-data")
with sqlite3.connect(DB) as db:
    AID_ANA = db.execute("SELECT id FROM archivos WHERE vehiculo_id = ?", (VID_ANA,)).fetchone()[0]
    RID_ANA = db.execute("SELECT id FROM registros WHERE vehiculo_id = ?", (VID_ANA,)).fetchone()[0]
    DID_ANA = None
ana.post(f"/vehiculo/{VID_ANA}/documentos", {"vence_vtv": "2027-05-01", "detalle_vtv": "x"})
ana.post(f"/vehiculo/{VID_ANA}/compartir", {"accion": "activar"})
with sqlite3.connect(DB) as db:
    TOKEN_ANA = db.execute("SELECT share_token FROM vehiculos WHERE id = ?", (VID_ANA,)).fetchone()[0]
    docs = db.execute("SELECT id FROM documentos WHERE vehiculo_id = ?", (VID_ANA,)).fetchall()
    DID_ANA = docs[0][0] if docs else None

# ============================================================================ 1. ENCABEZADOS Y COOKIES
print("\n== Encabezados y cookies ==")
resp = atacante.get("/login")
h = resp.headers
for nombre, motivo in (("Content-Security-Policy", "sin CSP, un XSS tendría vía libre"),
                       ("X-Content-Type-Options", "el navegador puede adivinar tipos (MIME sniffing)"),
                       ("Referrer-Policy", "los links externos reciben la URL completa (incluye tokens de /c/...)"),
                       ("Permissions-Policy", "sin restringir cámara, micrófono, ubicación")):
    if nombre not in h:
        hallazgo("SEGURIDAD", f"Falta {nombre}: {motivo}")
if "X-Frame-Options" not in h and "frame-ancestors" not in h.get("Content-Security-Policy", ""):
    hallazgo("SEGURIDAD", "La página se puede meter en un iframe de otro sitio (clickjacking): falta X-Frame-Options/frame-ancestors")
if "Strict-Transport-Security" not in h:
    hallazgo("SEGURIDAD", "Falta Strict-Transport-Security (HSTS): el navegador no obliga a usar HTTPS")
cookie = ana.get("/cuenta").headers  # la cookie se emite al crear la sesión
sc = [v for k, v in ana.post("/login", {"usuario": "x", "clave": "y"}, ruta_token="/login").headers.items() if k == "Set-Cookie"]
if not app.config.get("SESSION_COOKIE_SECURE"):
    hallazgo("SEGURIDAD", "La cookie de sesión no tiene el atributo Secure (viajaría por HTTP si alguien entra sin https)")
for ruta in ("/", "/cuenta", f"/vehiculo/{VID_ANA}", f"/vehiculo/{VID_ANA}/libro", "/vehiculo/nuevo"):
    cc = ana.get(ruta).headers.get("Cache-Control", "")
    if "no-store" not in cc:
        hallazgo("SEGURIDAD", f"{ruta} es una página privada pero no pide «no-store» (el botón Atrás podría mostrarla tras cerrar sesión): Cache-Control='{cc}'")
        break

# ============================================================================ 2. CSRF EN TODAS LAS RUTAS POST
print("\n== CSRF ==")
sin_token = []
for regla in app.url_map.iter_rules():
    if "POST" not in regla.methods or regla.endpoint == "static":
        continue
    ruta = re.sub(r"<(?:int:)?[a-z_]+>", "1", regla.rule)
    r = ana.c.post(ruta, data={})
    if r.status_code != 400:
        sin_token.append(f"{ruta} → {r.status_code}")
if sin_token:
    hallazgo("SEGURIDAD", "Rutas POST que aceptan pedidos sin token CSRF: " + ", ".join(sin_token))

# ============================================================================ 3. IDOR: bob contra los datos de ana
print("\n== Aislamiento entre cuentas ==")
hdr = {"X-CSRF-Token": token_de(bob.c, "/cuenta")}
accesos = [("GET", f"/vehiculo/{VID_ANA}"), ("GET", f"/vehiculo/{VID_ANA}/editar"), ("GET", f"/vehiculo/{VID_ANA}/libro"),
           ("GET", f"/vehiculo/{VID_ANA}/estadisticas"), ("GET", f"/vehiculo/{VID_ANA}/compartir"),
           ("GET", f"/vehiculo/{VID_ANA}/documentos"), ("GET", f"/vehiculo/{VID_ANA}/transferir"),
           ("GET", f"/vehiculo/{VID_ANA}/exportar"), ("GET", f"/vehiculo/{VID_ANA}/registro/nuevo"),
           ("GET", f"/registro/{RID_ANA}/editar"), ("GET", f"/archivo/{AID_ANA}"),
           ("POST", f"/vehiculo/{VID_ANA}/editar"), ("POST", f"/vehiculo/{VID_ANA}/foto"),
           ("POST", f"/vehiculo/{VID_ANA}/eliminar"), ("POST", f"/vehiculo/{VID_ANA}/compartir"),
           ("POST", f"/vehiculo/{VID_ANA}/transferir"), ("POST", f"/vehiculo/{VID_ANA}/documentos"),
           ("POST", f"/vehiculo/{VID_ANA}/boveda"), ("POST", f"/vehiculo/{VID_ANA}/registro/nuevo"),
           ("POST", f"/registro/{RID_ANA}/editar"), ("POST", f"/registro/{RID_ANA}/eliminar"),
           ("POST", f"/archivo/{AID_ANA}/eliminar")]
if DID_ANA:
    accesos.append(("POST", f"/documento/{DID_ANA}/renovar"))
for metodo, ruta in accesos:
    r = bob.c.get(ruta) if metodo == "GET" else bob.c.post(ruta, data={"csrf": hdr["X-CSRF-Token"], "titulo": "x"})
    if r.status_code not in (404,):
        hallazgo("SEGURIDAD", f"IDOR: bob pudo hacer {metodo} {ruta} sobre datos de ana → {r.status_code}")
# el orden de bob no toca el vehículo de ana
bob.c.post("/vehiculos/orden", data={"ids": str(VID_ANA)}, headers=hdr)
with sqlite3.connect(DB) as db:
    if db.execute("SELECT usuario_id FROM vehiculos WHERE id = ?", (VID_ANA,)).fetchone()[0] is None:
        hallazgo("SEGURIDAD", "el endpoint de orden alteró un vehículo ajeno")
# anónimo
for ruta in (f"/archivo/{AID_ANA}", f"/vehiculo/{VID_ANA}", "/cuenta", "/cuenta/exportar", "/vehiculos/orden"):
    r = atacante.get(ruta)
    if r.status_code not in (302, 405):
        hallazgo("SEGURIDAD", f"{ruta} responde {r.status_code} a un visitante sin sesión")
# el link compartido no filtra lo privado
html = atacante.get(f"/c/{TOKEN_ANA}").get_data(as_text=True)
visible = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
for privado in ("cedula", "Bóveda", "VTV", "ana_auditoria", "/vehiculo/"):
    if privado.lower() in visible.lower():
        hallazgo("SEGURIDAD", f"el link compartido muestra «{privado}»")
if atacante.get(f"/c/{TOKEN_ANA}/archivo/{AID_ANA}").status_code != 404:
    hallazgo("SEGURIDAD", "un archivo de la bóveda se puede bajar con el link compartido")

# ============================================================================ 4. XSS Y INYECCIÓN
print("\n== XSS e inyección ==")
CARGAS = ['<script>alert(1)</script>', '"><img src=x onerror=alert(1)>', "'-alert(1)-'", "</textarea><script>alert(1)</script>",
          "{{7*7}}", "${7*7}", "<svg/onload=alert(1)>", "javascript:alert(1)"]
for i, carga in enumerate(CARGAS):
    r = ana.post(f"/vehiculo/{VID_ANA}/editar", {"nombre": carga, "marca": carga, "modelo": carga, "version": carga,
                                                  "notas": carga, "patente": carga, "color": carga, "motor": carga,
                                                  "vin": carga, "aceite": carga, "km_inicial": "1000"})
    ana.post(f"/vehiculo/{VID_ANA}/registro/nuevo", {"titulo": carga, "detalle": carga, "taller": carga, "hecho_por": "taller",
                                                      "fecha": "2026-02-01", "km": "6000"})
    ana.post(f"/vehiculo/{VID_ANA}/documentos", {"detalle_vtv": carga, "vence_vtv": "2027-05-01"})
paginas = ["/", f"/vehiculo/{VID_ANA}", f"/vehiculo/{VID_ANA}/editar", f"/vehiculo/{VID_ANA}/libro", f"/vehiculo/{VID_ANA}/estadisticas",
           f"/vehiculo/{VID_ANA}/compartir", f"/vehiculo/{VID_ANA}/documentos", f"/vehiculo/{VID_ANA}/transferir",
           f"/registro/{RID_ANA}/editar", f"/vehiculo/{VID_ANA}/registro/nuevo", "/cuenta"]
ana.post(f"/vehiculo/{VID_ANA}/compartir", {"accion": "activar"})
paginas.append(f"/c/{TOKEN_ANA}")
for p in paginas:
    resp = ana.get(p)
    html = resp.get_data(as_text=True)
    # etiquetas ejecutables crudas fuera de los <script> propios de la app
    sin_scripts = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)
    for malo in ("<script>alert(1)", "<img src=x onerror", "<svg/onload"):
        if malo in sin_scripts:
            hallazgo("SEGURIDAD", f"XSS: {p} deja pasar «{malo}» sin escapar")
            break
    if "49" in re.findall(r"\b49\b", re.sub(r"<[^>]+>", " ", sin_scripts)) and "{{7*7}}" not in html and "${7*7}" not in html:
        hallazgo("SEGURIDAD", f"Inyección de plantillas en {p}: «{{{{7*7}}}}» se evaluó")
    if resp.status_code >= 500:
        hallazgo("ROMPE", f"{p} da {resp.status_code} con textos raros cargados")
# dentro de <script> (datos pasados a JS)
html = ana.get(f"/vehiculo/{VID_ANA}/editar").get_data(as_text=True)
if re.search(r"<script[^>]*>[^<]*</script><script>alert", html):
    hallazgo("SEGURIDAD", "XSS dentro de un bloque <script> del formulario de edición")
# calendario y exportaciones
ana.post("/cuenta/calendario", {})
with sqlite3.connect(DB) as db:
    CAL = db.execute("SELECT cal_token FROM usuarios WHERE usuario = 'ana_auditoria'").fetchone()[0]
ics = atacante.get(f"/cal/{CAL}.ics").get_data(as_text=True)
if re.search(r"^(SUMMARY|DESCRIPTION):.*<script", ics, flags=re.M) is None and "\nBEGIN:VEVENT" in ics:
    pass
if re.search(r"\r\n[A-Z-]+:.*\r\n(BEGIN:VEVENT\r\nATTACH|ATTENDEE)", ics):
    hallazgo("SEGURIDAD", "inyección de líneas en el calendario .ics")
# inyección de líneas en .ics con saltos de línea en el título
ana.post(f"/vehiculo/{VID_ANA}/registro/nuevo", {"titulo": "Control\r\nATTENDEE:mailto:x@x.com", "prox_fecha": "2027-01-01", "fecha": "2026-03-01"})
ics = atacante.get(f"/cal/{CAL}.ics").get_data(as_text=True)
if re.search(r"^ATTENDEE:", ics, flags=re.M):
    hallazgo("SEGURIDAD", "inyección en el .ics: un título con salto de línea agrega propiedades al evento")
# CSV con fórmulas
ana.post(f"/vehiculo/{VID_ANA}/registro/nuevo", {"titulo": "=HYPERLINK(\"http://x\",\"a\")", "detalle": "+cmd|' /C calc'!A0",
                                                  "fecha": "2026-03-02"})
import zipfile  # noqa: E402
z = zipfile.ZipFile(io.BytesIO(ana.get("/cuenta/exportar").data))
csv_txt = next(z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".csv"))
for linea in csv_txt.splitlines()[1:]:
    for celda in linea.split(";"):
        if celda[:1] in ("=", "+", "-", "@"):
            hallazgo("SEGURIDAD", f"inyección de fórmulas en el CSV exportado: «{celda[:30]}»")
            break
# SQL injection por parámetros
for q in ("' OR 1=1 --", "%' UNION SELECT usuario,clave,1,1,1,1,1,1,1,1,1,1,1,1 FROM usuarios --", "\"; DROP TABLE registros; --"):
    r = ana.get(f"/vehiculo/{VID_ANA}", query_string={"q": q, "cat": q, "anio": q})
    if r.status_code >= 500 or "pbkdf2" in r.get_data(as_text=True) or "scrypt" in r.get_data(as_text=True):
        hallazgo("SEGURIDAD", f"posible inyección SQL con q={q[:20]!r} → {r.status_code}")
with sqlite3.connect(DB) as db:
    db.execute("SELECT COUNT(*) FROM registros")  # la tabla sigue existiendo
# usuario con SQL
r = atacante.post("/login", data={"csrf": token_de(atacante, "/login"), "usuario": "' OR '1'='1", "clave": "x"})
if r.status_code == 302:
    hallazgo("SEGURIDAD", "el login se pudo saltear con inyección SQL")

# ============================================================================ 5. AUTENTICACIÓN
print("\n== Autenticación ==")
def login_resp(usuario, clave):
    c = app.test_client()
    return c.post("/login", data={"csrf": token_de(c, "/login"), "usuario": usuario, "clave": clave})
t0 = time.perf_counter(); login_resp("no_existe_nadie", "x" * 10); t_no = time.perf_counter() - t0
t0 = time.perf_counter(); login_resp("ana_auditoria", "x" * 10); t_si = time.perf_counter() - t0
r1, r2 = login_resp("no_existe_nadie", "abcdefg"), login_resp("ana_auditoria", "abcdefg")
def normal(r):
    t = re.sub(r"ana_auditoria|no_existe_nadie", "", r.get_data(as_text=True))
    t = re.sub(r'(csrf"[^>]*?(?:value|content)=")[^"]+', r"\1", t)
    t = re.sub(r'nonce="[^"]+"', "", t)
    return re.sub(r"\s+", "", t)


if normal(r1) != normal(r2):
    hallazgo("SEGURIDAD", "el login responde distinto si el usuario existe o no (permite enumerar usuarios)")
if t_si > t_no * 5 and t_si > 0.05:
    hallazgo("SEGURIDAD", f"el login tarda {t_si * 1000:.0f} ms con usuario real y {t_no * 1000:.0f} ms con usuario inexistente: se puede enumerar por tiempo")
# contraseña gigante: no debe costar mucho CPU ni romper
t0 = time.perf_counter(); r = login_resp("ana_auditoria", "A" * 2_000_000); dt = time.perf_counter() - t0
if r.status_code >= 500 or dt > 2:
    hallazgo("ROMPE", f"login con contraseña de 2 MB: {r.status_code} en {dt:.1f} s (DoS por hashing de contraseñas enormes)")
# bloqueo no se esquiva cambiando mayúsculas / espacios / unicode
c = app.test_client(); tok = token_de(c, "/login")
for variante in ("ana_auditoria", "ANA_AUDITORIA", " ana_auditoria ", "Ana_Auditoria", "ana_auditoria​", "ana_auditoria",
                 "Ana_auditoria", "aNa_auditoria"):
    c.post("/login", data={"csrf": tok, "usuario": variante, "clave": "mal"})
r = c.post("/login", data={"csrf": tok, "usuario": "ana_auditoria", "clave": "clave-larga-1"})
if r.status_code == 302:
    hallazgo("SEGURIDAD", "el límite de intentos de ingreso se puede esquivar variando mayúsculas o espacios del usuario")
nucleo.INTENTOS.clear()
# bloqueo como DoS: cualquiera puede bloquearle la cuenta a otro desde otra IP
c2 = app.test_client(); tok2 = token_de(c2, "/login")
for _ in range(6):
    c2.post("/login", data={"csrf": tok2, "usuario": "ana_auditoria", "clave": "mal"}, headers={"X-Real-IP": "203.0.113.5"})
c3 = Sesion(); c3_tok = token_de(c3.c, "/login")
r = c3.c.post("/login", data={"csrf": c3_tok, "usuario": "ana_auditoria", "clave": "clave-larga-1"},
              headers={"X-Real-IP": "198.51.100.7"})
if r.status_code == 429:
    hallazgo("SEGURIDAD", "bloqueo de cuenta por usuario (sin considerar la IP): cualquiera puede dejar fuera a un usuario real "
                          "con 5 intentos fallidos cada 10 minutos (denegación de servicio dirigida)")
nucleo.INTENTOS.clear()
# prueba de contraseñas repartida entre muchas IP contra un usuario: debe frenarse igual
c5 = app.test_client(); tok5 = token_de(c5, "/login"); frenado5 = False
for i in range(60):
    r = c5.post("/login", data={"csrf": tok5, "usuario": "ana_auditoria", "clave": f"intento{i}"},
                headers={"X-Real-IP": f"192.0.2.{i}"})
    if r.status_code == 429:
        frenado5 = True
        break
if not frenado5:
    hallazgo("SEGURIDAD", "60 intentos de contraseña repartidos entre 60 IP distintas contra un usuario no se frenaron")
nucleo.INTENTOS.clear()
# (El límite de cuentas por IP confía en X-Real-IP, que el proxy del hosting debe sobrescribir: eso se
# comprueba contra el sitio publicado, no en local.)
# sesión: cookie manipulada
c = app.test_client()
c.set_cookie("session", "eyJ1aWQiOjF9.AAAAAA.AAAAAAAAAAAAAAAAAAAAAAAAAAA")
if c.get("/cuenta").status_code != 302:
    hallazgo("SEGURIDAD", "una cookie de sesión falsificada fue aceptada")
# clave secreta por defecto
if app.secret_key == "cambiame-por-una-clave-secreta":
    hallazgo("SEGURIDAD", "SECRET_KEY por defecto en uso (en producción se genera sola, pero localmente es predecible)")
# cierre de sesión realmente cierra
s = Sesion("sesion_auditoria"); s.post("/logout")
if s.get("/cuenta").status_code != 302:
    hallazgo("SEGURIDAD", "después de /logout la sesión seguía activa")
if "GET" in [m for r in app.url_map.iter_rules() if r.rule == "/logout" for m in r.methods]:
    hallazgo("SEGURIDAD", "/logout se hace con GET: cualquier sitio puede cerrarte la sesión con una imagen (logout CSRF; riesgo bajo)")
# redirecciones abiertas
for destino in ("//evil.com", "https://evil.com", "/\\evil.com", "///evil.com", "javascript:alert(1)", "\\\\evil.com", "/%2f/evil.com"):
    c = app.test_client(); tok = token_de(c, "/login")
    r = c.post(f"/login?next={destino}", data={"csrf": tok, "usuario": "sesion_auditoria", "clave": "clave-larga-1"})
    loc = r.headers.get("Location", "")
    if r.status_code == 302 and (loc.startswith("//") or "evil" in loc or loc.startswith("javascript") or loc.startswith("/\\")):
        hallazgo("SEGURIDAD", f"redirección abierta tras el login con next={destino!r} → {loc}")

# ============================================================================ 6. ARCHIVOS SUBIDOS
print("\n== Archivos ==")
def subir(contenido, nombre, mime="image/png", ruta=None):
    return ana.post(ruta or f"/vehiculo/{VID_ANA}/boveda", {"categoria": "cedula", "archivos": (io.BytesIO(contenido), nombre, mime)},
                    headers={"X-CSRF-Token": token_de(ana.c, "/cuenta")}, content_type="multipart/form-data")
def ultimo_archivo():
    with sqlite3.connect(DB) as db:
        return db.execute("SELECT id, archivo, mime FROM archivos ORDER BY id DESC LIMIT 1").fetchone()
def cantidad():
    with sqlite3.connect(DB) as db:
        return db.execute("SELECT COUNT(*) FROM archivos").fetchone()[0]

malos = {"html.png": b"<html><script>alert(1)</script></html>", "svg.png": b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
         "php.png": b"<?php system($_GET['c']); ?>", "exe.png": b"MZ\x90\x00" + b"\x00" * 100,
         "vacio.png": b"", "gif_malo.png": b"GIF89a<script>alert(1)</script>"}
for nombre, contenido in malos.items():
    antes = cantidad(); r = subir(contenido, nombre)
    if r.status_code >= 500:
        hallazgo("ROMPE", f"subir {nombre} produce {r.status_code}")
    if cantidad() > antes:
        a = ultimo_archivo()
        hallazgo("SEGURIDAD", f"se aceptó un archivo falso ({nombre}) guardado como {a[2]}")
# polyglot: PNG válido con HTML al final -> se reescribe al achicar
poli = PNG_OK + b"<script>alert(1)</script>"
subir(poli, "poli.png")
a = ultimo_archivo()
with open(os.path.join(os.environ["UPLOAD_DIR"], a[1]), "rb") as f:
    if b"<script>" in f.read():
        hallazgo("SEGURIDAD", "un archivo con HTML escondido al final quedó guardado tal cual (poliglota)")
# PDF con JavaScript: se entrega con Content-Disposition/CSP?
subir(b"%PDF-1.4\n1 0 obj<</S/JavaScript/JS(app.alert(1))>>endobj\n%%EOF", "js.pdf", "application/pdf")
a = ultimo_archivo()
r = ana.get(f"/archivo/{a[0]}")
if "nosniff" not in r.headers.get("X-Content-Type-Options", "") and "Content-Security-Policy" not in r.headers:
    hallazgo("SEGURIDAD", "los archivos se sirven sin X-Content-Type-Options ni CSP (un PDF/imagen mal interpretado podría ejecutarse)")
if r.headers.get("Content-Type", "").startswith("text/html"):
    hallazgo("SEGURIDAD", "un archivo subido se sirve como text/html")
# bomba de descompresión
for (w, h) in ((20000, 20000), (60000, 60000), (9000, 9000)):
    antes = cantidad()
    bomba = pixel_png(w, h)
    t0 = time.perf_counter()
    try:
        r = subir(bomba, f"bomba_{w}.png")
        dt = time.perf_counter() - t0
        if cantidad() > antes:
            hallazgo("SEGURIDAD", f"se aceptó una imagen de {w}x{h} px ({w * h / 1e6:.0f} megapíxeles)")
        if r.status_code >= 500 or dt > 15:
            hallazgo("ROMPE", f"imagen de {w}×{h} px (bomba de descompresión): {r.status_code} en {dt:.1f} s")
    except Exception as e:  # noqa: BLE001
        hallazgo("ROMPE", f"imagen de {w}×{h} px tumbó el pedido: {type(e).__name__}: {e}")
# nombres de archivo hostiles
for nombre in ("../../../etc/passwd.png", "..\\..\\app.py.png", "a" * 5000 + ".png", "x\x00.png", "con espacios y ñ ü 😀.png", "CON.png"):
    r = subir(PNG_OK, nombre)
    if r.status_code >= 500:
        hallazgo("ROMPE", f"nombre de archivo raro {nombre[:30]!r} → {r.status_code}")
carpeta = os.environ["UPLOAD_DIR"]
fuera = [n for n in os.listdir(os.path.dirname(carpeta)) if n.endswith(".png") or n.endswith(".py")]
if fuera:
    hallazgo("SEGURIDAD", f"path traversal: se escribieron archivos fuera de uploads/: {fuera}")
# demasiados archivos de una vez / pedido enorme
r = ana.post(f"/vehiculo/{VID_ANA}/boveda", {"categoria": "otro", "archivos": [(io.BytesIO(PNG_OK), f"{i}.png") for i in range(300)]},
             headers={"X-CSRF-Token": token_de(ana.c, "/cuenta")}, content_type="multipart/form-data")
if r.status_code >= 500:
    hallazgo("ROMPE", f"300 archivos en un solo pedido → {r.status_code}")
r = subir(b"\x00" * (46 * 1024 * 1024), "enorme.png")
if r.status_code not in (413, 302):
    hallazgo("ROMPE", f"archivo de 46 MB → {r.status_code}")
# cupo: no se puede pasar de 100 MB subiendo en paralelo
# (se verifica la contabilidad con PDF grandes de 9 MB)
pdf9 = b"%PDF-1.4\n" + b"0" * (9 * 1024 * 1024) + b"\n%%EOF"
for _ in range(14):
    subir(pdf9, "grande.pdf", "application/pdf")
with sqlite3.connect(DB) as db:
    usado = db.execute("SELECT COALESCE(SUM(a.bytes),0) FROM archivos a JOIN vehiculos v ON v.id = a.vehiculo_id WHERE v.usuario_id = "
                       "(SELECT id FROM usuarios WHERE usuario = 'ana_auditoria')").fetchone()[0]
if usado > 100 * 1024 * 1024 * 1.02:
    hallazgo("SEGURIDAD", f"se superó el cupo de 100 MB: {usado / 1048576:.0f} MB guardados")
# archivos de otro: el nombre en disco no es adivinable
a = ultimo_archivo()
if not re.fullmatch(r"[0-9a-f]{16,}\.\w+", a[1]):
    hallazgo("SEGURIDAD", f"el nombre del archivo en disco es predecible: {a[1]}")
# transversal por ruta
for ruta in ("/archivo/../../etc/passwd", "/static/../app.py", "/static/..%2fapp.py", "/static/%2e%2e/nucleo.py",
             "/static/vendor/../../bitacora.db", "/uploads/", "/respaldos/", "/.secret_key", "/bitacora.db", "/app.py",
             "/static/%00.js", "/../app.py"):
    r = atacante.get(ruta)
    if r.status_code == 200 and (b"import " in r.data[:2000] or b"SQLite" in r.data[:100] or "bitacora" in ruta):
        hallazgo("SEGURIDAD", f"se expone un archivo interno en {ruta}")

# ============================================================================ 7. TRANSFERENCIA Y TOKENS
print("\n== Transferencias y tokens ==")
r = ana.post(f"/vehiculo/{VID_ANA}/transferir", {})
cod = re.search(r'id="codigo-transfer">([A-Z0-9-]+)<', r.get_data(as_text=True)).group(1)
# fuerza bruta: muchos intentos seguidos desde la misma cuenta deben frenarse
c4 = Sesion("fuerza_bruta"); frenado = False
for i in range(12):
    rr = c4.post("/recibir", {"codigo": f"AAAA-BBBB-CC{i:02d}"[:14]}, ruta_token="/recibir")
    if rr.status_code == 429:
        frenado = True; break
if not frenado:
    hallazgo("SEGURIDAD", "/recibir no frena la fuerza bruta de códigos de transferencia")
# …pero se puede esquivar creando otra cuenta por intento (límite por IP/altas)
# doble canje simultáneo: dos cuentas con el mismo código; solo una debe quedarse el auto
resultados = []
cuentas = [Sesion(f"canje_{i}") for i in range(4)]
def canjear(s):
    rr = s.post("/recibir", {"codigo": cod}, ruta_token="/recibir")
    resultados.append(rr.status_code)
hilos = [threading.Thread(target=canjear, args=(s,)) for s in cuentas]
[h.start() for h in hilos]; [h.join() for h in hilos]
if resultados.count(302) > 1:
    hallazgo("SEGURIDAD", f"carrera en la transferencia: {resultados.count(302)} cuentas canjearon el mismo código a la vez")
# entropía de tokens
for nombre, valor in (("link compartido", TOKEN_ANA), ("calendario", CAL)):
    if len(valor) < 16:
        hallazgo("SEGURIDAD", f"el token de {nombre} es corto ({len(valor)} caracteres)")
# el código de recuperación y la clave se guardan hasheados
with sqlite3.connect(DB) as db:
    claves = db.execute("SELECT clave, codigo FROM usuarios").fetchall()
for clave, codigo in claves:
    if "clave-larga-1" in (clave or "") or not (clave or "").startswith(("scrypt:", "pbkdf2:")):
        hallazgo("SEGURIDAD", "una contraseña no está hasheada correctamente")
    if codigo and not codigo.startswith(("scrypt:", "pbkdf2:")):
        hallazgo("SEGURIDAD", "un código de recuperación no está hasheado")
with sqlite3.connect(DB) as db:
    for (tc,) in db.execute("SELECT transfer_codigo FROM vehiculos WHERE transfer_codigo IS NOT NULL"):
        if not tc.startswith(("scrypt:", "pbkdf2:")):
            hallazgo("SEGURIDAD", "un código de transferencia está guardado en claro")

# ============================================================================ 8. ROMPER: ENTRADAS EXTREMAS
print("\n== Entradas extremas ==")
EXTREMOS = ["", " ", "0", "-1", "-0", "1e999", "nan", "inf", "-inf", "99999999999999999999999999", "9" * 400, "1.5", "0x10", "١٢٣", "😀" * 500,
            "A" * 100_000, "\x00", "\x00\x01\x02", "'\"\\", "<>&", "2026-02-30", "0000-00-00", "9999-12-31", "1900-01-01", "2026-13-45",
            "%s%s%s%n", "{0}", "‮⁦", "\n\r\n", "NULL", "None", "true", "[]", "{}", "../", "%00", "ÿ" * 1000]
CAMPOS_VEH = ["nombre", "marca", "modelo", "version", "anio", "patente", "km_inicial", "notas", "color", "carroceria", "transmision", "motor",
              "combustible", "tanque", "codigo_pintura", "vin", "bujias", "aceite", "aceite_litros", "refrigerante", "frenos", "neumaticos",
              "presion_del", "presion_tras", "uso", "km_mes", "imagen_modo", "foto_x", "foto_y", "foto_zoom", "foto_ajuste", "calcular_uso"]
CAMPOS_REG = ["fecha", "km", "categoria", "titulo", "detalle", "costo", "hecho_por", "taller", "prox_km", "prox_fecha"]
rotos = {}
for valor in EXTREMOS:
    for ruta, campos in ((f"/vehiculo/{VID_ANA}/editar", CAMPOS_VEH), (f"/vehiculo/{VID_ANA}/registro/nuevo", CAMPOS_REG),
                         (f"/registro/{RID_ANA}/editar", CAMPOS_REG), ("/vehiculo/nuevo", CAMPOS_VEH),
                         (f"/vehiculo/{VID_ANA}/documentos", ["vence_vtv", "detalle_vtv", "vence_seguro", "cada_seguro", "vence_patente"])):
        try:
            r = ana.post(ruta, {c: valor for c in campos})
        except Exception as e:  # noqa: BLE001
            rotos.setdefault((ruta, "excepción"), []).append(f"{type(e).__name__} con {valor[:15]!r}"); continue
        if r.status_code >= 500:
            rotos.setdefault((ruta, r.status_code), []).append(valor[:20])
        # y cada campo por separado en la ficha: encuentra al culpable
for (ruta, codigo), valores in rotos.items():
    hallazgo("ROMPE", f"POST {re.sub(r'/\d+', '/N', ruta)} da {codigo} con entradas como {valores[:4]}")
# campo por campo con los valores numéricos peligrosos
culpables = set()
for campo in CAMPOS_VEH:
    for valor in ("99999999999999999999999999", "1e999", "nan", "-5", "0", "\x00"):
        base = {"marca": "Ford", "modelo": "Focus", "km_inicial": "10"}
        base[campo] = valor
        r = ana.post(f"/vehiculo/{VID_ANA}/editar", base)
        if r.status_code >= 500:
            culpables.add((campo, valor[:12]))
for campo in CAMPOS_REG:
    for valor in ("99999999999999999999999999", "1e999", "nan", "-5", "\x00", "9" * 400):
        base = {"titulo": "t", "fecha": "2026-03-01"}
        base[campo] = valor
        r = ana.post(f"/vehiculo/{VID_ANA}/registro/nuevo", base)
        if r.status_code >= 500:
            culpables.add((f"registro.{campo}", valor[:12]))
if culpables:
    hallazgo("ROMPE", "campos que causan error 500: " + ", ".join(f"{c}={v!r}" for c, v in sorted(culpables)))
# después de todo eso las páginas deben seguir abriendo
for p in paginas:
    r = ana.get(p)
    if r.status_code >= 500:
        hallazgo("ROMPE", f"{p} quedó rota ({r.status_code}) después de guardar datos extremos")
# parámetros de URL extremos
rutas_get = ["/", "/vehiculo/{v}", "/vehiculo/{v}/libro", "/vehiculo/{v}/estadisticas", "/vehiculo/{v}/compartir",
             "/vehiculo/{v}/documentos", "/registro/{r}/editar", "/archivo/{a}", "/cuenta", "/privacidad", "/terminos", "/recibir",
             "/vehiculo/{v}/transferir", "/vehiculo/{v}/registro/nuevo", "/c/{t}", "/cal/{c}.ics", "/sw.js", "/vehiculo/{v}/exportar"]
for plantilla in rutas_get:
    ruta = plantilla.format(v=VID_ANA, r=RID_ANA, a=AID_ANA, t=TOKEN_ANA, c=CAL)
    for q in ({"q": "A" * 50_000}, {"cat": "\x00"}, {"anio": "-1"}, {"anio": "9" * 50}, {"q": "%"}, {"q": "_"}, {"x": "1"} , {"q": "\ud800"} if False else {"q": "ñ"}):
        r = ana.get(ruta, query_string=q)
        if r.status_code >= 500:
            hallazgo("ROMPE", f"GET {plantilla} con {str(q)[:30]} → {r.status_code}")
for ruta in ("/vehiculo/0", "/vehiculo/-1", "/vehiculo/99999999999999999999", "/vehiculo/abc", "/registro/0/editar", "/archivo/-5",
             "/c/", "/c/" + "a" * 5000, "/cal/x.ics", "/cal/" + "a" * 5000 + ".ics", "/" + "a" * 20000, "/vehiculo/1/../2", "/%", "/%ff"):
    r = ana.get(ruta)
    if r.status_code >= 500:
        hallazgo("ROMPE", f"GET {ruta[:40]} → {r.status_code}")
for metodo in ("PUT", "DELETE", "PATCH", "OPTIONS", "TRACE"):
    r = ana.c.open("/", method=metodo)
    if r.status_code >= 500:
        hallazgo("ROMPE", f"{metodo} / → {r.status_code}")
# orden con basura
for ids in ("", ",,,", "a,b,c", "9" * 400, ",".join(str(i) for i in range(50_000)), "-1,0,1.5", "1;DROP"):
    r = ana.c.post("/vehiculos/orden", data={"ids": ids}, headers={"X-CSRF-Token": token_de(ana.c, "/cuenta")})
    if r.status_code >= 500:
        hallazgo("ROMPE", f"/vehiculos/orden con {ids[:20]!r} → {r.status_code}")
# cuerpos raros: JSON, multipart roto, content-length falso
for ctype, cuerpo in (("application/json", b'{"csrf": "x"}'), ("multipart/form-data; boundary=zzz", b"--zzz\r\ngarbage"),
                      ("application/x-www-form-urlencoded", b"%ZZ=%ZZ&&&=&a"), ("text/plain", b"x" * 1000)):
    for ruta in ("/login", "/registro", f"/vehiculo/{VID_ANA}/boveda", f"/vehiculo/{VID_ANA}/editar"):
        r = ana.c.post(ruta, data=cuerpo, content_type=ctype)
        if r.status_code >= 500:
            hallazgo("ROMPE", f"POST {ruta} con cuerpo {ctype} → {r.status_code}")

# ============================================================================ 9. CARGA, CONCURRENCIA Y TAMAÑO
print("\n== Carga y concurrencia ==")
muchos = Sesion("mucha_carga")
t0 = time.perf_counter()
for i in range(60):
    muchos.post("/vehiculo/nuevo", {"marca": "Fiat", "modelo": "Uno", "nombre": f"Auto {i}", "km_inicial": "100"})
t_alta = time.perf_counter() - t0
with sqlite3.connect(DB) as db:
    vid = db.execute("SELECT id FROM vehiculos WHERE nombre = 'Auto 0'").fetchone()[0]
    db.executemany("INSERT INTO registros (vehiculo_id, fecha, km, categoria, titulo, detalle, costo, prox_km) VALUES (?,?,?,?,?,?,?,?)",
                   [(vid, f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}", 1000 + i * 10, "control", f"Trabajo {i}", "d" * 200, 100.5, 2000 + i) for i in range(3000)])
for ruta in ("/", f"/vehiculo/{vid}", f"/vehiculo/{vid}/libro", f"/vehiculo/{vid}/estadisticas", "/cuenta/exportar"):
    t0 = time.perf_counter(); r = muchos.get(ruta); dt = time.perf_counter() - t0
    if r.status_code >= 500 or dt > 3:
        hallazgo("ROMPE", f"{ruta.replace(str(vid), 'N')} con 60 autos / 3.000 registros: {r.status_code} en {dt:.1f} s")
    else:
        print(f"  {ruta.replace(str(vid), 'N')}: {dt * 1000:.0f} ms")
t0 = time.perf_counter(); muchos.get(f"/vehiculo/{vid}", query_string={"q": "Trabajo"}); dt = time.perf_counter() - t0
# concurrencia: 40 hilos escribiendo a la vez en la misma base
errores = []
def escribir(i):
    try:
        s = app.test_client()
        tok = token_de(s, "/registro")
        r = s.post("/registro", data={"csrf": tok, "usuario": f"hilo_{i}", "clave": "clave-larga-1", "clave2": "clave-larga-1", "acepto": "1"})
        if r.status_code not in (302, 429):
            errores.append(f"alta {r.status_code}")
        for j in range(5):
            tok = token_de(s, "/cuenta")
            r = s.post("/vehiculo/nuevo", data={"csrf": tok, "marca": "VW", "modelo": "Gol", "nombre": f"h{i}-{j}", "km_inicial": "1"})
            if r.status_code >= 500:
                errores.append(f"vehículo {r.status_code}")
    except Exception as e:  # noqa: BLE001
        errores.append(f"{type(e).__name__}: {e}")
hilos = [threading.Thread(target=escribir, args=(i,)) for i in range(40)]
[h.start() for h in hilos]; [h.join() for h in hilos]
if errores:
    hallazgo("ROMPE", f"escrituras simultáneas: {len(errores)} fallas, por ejemplo {errores[:3]}")
with sqlite3.connect(DB) as db:
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        hallazgo("ROMPE", "la base quedó dañada después de las pruebas")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        hallazgo("ROMPE", "quedaron filas huérfanas (claves foráneas rotas)")
# borrar cuenta deja todo limpio, incluidos los archivos
s = Sesion("borrame"); s.post("/vehiculo/nuevo", {"marca": "Ford", "modelo": "Ka", "nombre": "x"})
with sqlite3.connect(DB) as db:
    vb = db.execute("SELECT id FROM vehiculos WHERE nombre = 'x'").fetchone()[0]
s.post(f"/vehiculo/{vb}/boveda", {"categoria": "otro", "archivos": (io.BytesIO(PNG_OK), "a.png")},
       headers={"X-CSRF-Token": token_de(s.c, "/cuenta")}, content_type="multipart/form-data")
with sqlite3.connect(DB) as db:
    arch = [r[0] for r in db.execute("SELECT archivo FROM archivos WHERE vehiculo_id = ?", (vb,))]
s.post("/cuenta", {"accion": "borrar", "confirmar": "borrame", "actual": "clave-larga-1"})
with sqlite3.connect(DB) as db:
    if db.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'borrame'").fetchone()[0] or \
            db.execute("SELECT COUNT(*) FROM vehiculos WHERE id = ?", (vb,)).fetchone()[0] or \
            db.execute("SELECT COUNT(*) FROM archivos WHERE vehiculo_id = ?", (vb,)).fetchone()[0]:
        hallazgo("ROMPE", "borrar la cuenta dejó datos en la base")
for nombre in arch:
    if os.path.exists(os.path.join(os.environ["UPLOAD_DIR"], nombre)):
        hallazgo("SEGURIDAD", "borrar la cuenta dejó los archivos en el disco (datos que el usuario pidió eliminar)")
# el token de calendario / link de un usuario borrado deja de andar
# usuarios con nombres difíciles
for nombre in ("a" * 31, "ab", "con espacio", "ñandú", "' OR 1=1", "<b>x</b>", "admin\x00", "ADMIN", "Ana_Auditoria"):
    c = app.test_client(); tok = token_de(c, "/registro")
    r = c.post("/registro", data={"csrf": tok, "usuario": nombre, "clave": "clave-larga-1", "clave2": "clave-larga-1", "acepto": "1"})
    if r.status_code >= 500:
        hallazgo("ROMPE", f"registro con usuario {nombre[:15]!r} → {r.status_code}")
    if r.status_code == 302 and nombre in ("Ana_Auditoria", "a" * 31, "ab", "con espacio", "ñandú", "' OR 1=1", "<b>x</b>"):
        hallazgo("SEGURIDAD", f"se creó una cuenta con un usuario inválido o duplicado por mayúsculas: {nombre[:20]!r}")

# ============================================================================ resumen
print("\n" + "=" * 70)
seg = [t for t in hallazgos if t[0] == "SEGURIDAD"]
rot = [t for t in hallazgos if t[0] == "ROMPE"]
print(f"Hallazgos: {len(seg)} de seguridad, {len(rot)} de robustez.")
if not hallazgos:
    print("SIN HALLAZGOS")
sys.exit(1 if hallazgos else 0)
