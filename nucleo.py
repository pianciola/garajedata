"""GarajeData — núcleo: la app Flask, la base, los filtros y las funciones comunes.

Las páginas están en rutas/ (una por tema) y se registran desde app.py.
"""
import csv
import hashlib
import io
import json
import math
import os
import re
import secrets
import sqlite3
import time
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Flask, Response, abort, flash, g, redirect, render_template,
                   request, send_file, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import archivos
import respaldos
from catalogo import canon_marca, canon_modelo, catalogo_js, equipamientos_de, logo_marca, logo_oscuro, tema_marca
from mantenimiento import (KM_MES_MAX, DOCUMENTOS, REPETICION_SUGERIDA, REPETICIONES, USOS, km_estimado,
                           km_por_mes, plan_mantenimiento, promedio_medido, sumar_meses, vencimientos)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "bitacora.db"))

app = Flask(__name__)


def clave_secreta():
    """SECRET_KEY del entorno o, si no hay, una clave al azar que se guarda en .secret_key (nunca una fija)."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    ruta = os.path.join(BASE_DIR, ".secret_key")
    try:
        with open(ruta, encoding="utf-8") as f:
            guardada = f.read().strip()
        if guardada:
            return guardada
    except OSError:
        pass
    nueva = secrets.token_hex(32)
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(nueva)
    except OSError:
        pass  # carpeta de solo lectura: clave temporal (las sesiones no sobreviven a un reinicio)
    return nueva


app.secret_key = clave_secreta()
# En el sitio publicado (HTTPS) la cookie viaja solo cifrada y el navegador obliga a usar HTTPS.
HTTPS = os.environ.get("GARAJEDATA_HTTPS") == "1"
# Lax: el navegador no manda la sesión en formularios enviados desde otros sitios.
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=HTTPS,
                  PERMANENT_SESSION_LIFETIME=timedelta(days=60),
                  MAX_CONTENT_LENGTH=45 * 1024 * 1024)

CATEGORIAS = {
    # Mantenimiento
    "control": "Service",
    "fluidos": "Aceite y fluidos",
    "piezas": "Repuestos",
    "neumaticos": "Neumáticos",
    "reparacion": "Reparación",
    "chapa": "Chapa y pintura",
    "accesorios": "Accesorios",
    "lavado": "Lavado",
    # Gastos y papeles
    "combustible": "Combustible",
    "seguro": "Seguro",
    "patente": "Patente",
    "vtv": "VTV / RTO",
    "estacionamiento": "Cochera y peajes",
    "multas": "Multas",
    "tramites": "Trámites",
    "otro": "Otro",
}

# Ayuda corta debajo de cada botón del formulario.
AYUDA_CATEGORIAS = {
    "control": "Revisión, diagnóstico", "fluidos": "Aceite, refrigerante",
    "piezas": "Filtros, pastillas, batería", "neumaticos": "Cubiertas, alineación",
    "reparacion": "Algo que se rompió", "chapa": "Choques, rayones",
    "accesorios": "Audio, alarma, mejoras", "lavado": "Lavado, pulido",
    "combustible": "Nafta, diésel, GNC", "seguro": "Cuota o póliza",
    "patente": "Impuesto automotor", "vtv": "Verificación técnica",
    "estacionamiento": "Estacionamiento, peajes", "multas": "Infracciones",
    "tramites": "Transferencia, gestoría", "otro": "Lo que no entra arriba",
}

# Categorías que ya no existen y en cuál quedaron (registros viejos y copias importadas).
CATEGORIAS_VIEJAS = {"modificacion": "accesorios", "peajes": "estacionamiento"}

GRUPOS_CATEGORIAS = (
    ("Mantenimiento", ("control", "fluidos", "piezas", "neumaticos", "reparacion", "chapa", "accesorios", "lavado")),
    ("Gastos y papeles", ("combustible", "seguro", "patente", "vtv", "estacionamiento", "multas", "tramites", "otro")),
)

TRANSMISIONES = {"manual": "Manual", "automatica": "Automática"}
COMBUSTIBLES = {"nafta": "Nafta", "diesel": "Diésel", "gnc": "GNC + nafta",
                "hibrido": "Híbrido", "electrico": "Eléctrico"}
FRENOS = ["DOT 3", "DOT 4", "DOT 5.1"]
HECHO_POR = {"taller": "Taller / mecánico", "yo": "Hecho por mí", "otro": "Otro"}

CARROCERIAS = {
    "moto": "Moto",
    "hatchback": "Hatchback",
    "sedan": "Sedán",
    "rural": "Rural / Familiar",
    "coupe": "Coupé",
    "suv": "SUV / Todoterreno",
    "pickup": "Pick-up",
    "utilitario": "Utilitario / Furgón",
}
COLOR_DEFAULT = "#2e6fd8"
COLORES = {
    "#f2f2f0": "Blanco", "#b8bcc2": "Gris plata", "#4a4f57": "Gris oscuro",
    "#16181c": "Negro", "#c0262d": "Rojo", "#2e6fd8": "Azul",
    "#1f3a5f": "Azul marino", "#2f6b3a": "Verde", "#e8a317": "Amarillo",
    "#e8590c": "Naranja", "#7a1f2b": "Bordó", "#c9b38a": "Champagne",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario  TEXT NOT NULL UNIQUE COLLATE NOCASE,
    clave    TEXT NOT NULL,
    creado   TEXT NOT NULL,
    codigo   TEXT
);
CREATE TABLE IF NOT EXISTS vehiculos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    marca       TEXT,
    modelo      TEXT,
    anio        INTEGER,
    patente     TEXT,
    km_inicial  INTEGER,
    notas       TEXT,
    carroceria  TEXT,
    color       TEXT,
    version     TEXT,
    transmision TEXT,
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS sesiones (
    token TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    vence REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS documentos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos(id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL,
    vence       TEXT,
    cada_meses  INTEGER,
    detalle     TEXT,
    UNIQUE (vehiculo_id, tipo)
);
CREATE TABLE IF NOT EXISTS pendientes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos(id) ON DELETE CASCADE,
    titulo      TEXT NOT NULL,
    categoria   TEXT,
    fecha       TEXT,
    km          INTEGER,
    detalle     TEXT,
    creado      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS archivos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos(id) ON DELETE CASCADE,
    registro_id INTEGER REFERENCES registros(id) ON DELETE CASCADE,
    categoria   TEXT,
    nombre      TEXT NOT NULL,
    archivo     TEXT NOT NULL,
    mime        TEXT NOT NULL,
    bytes       INTEGER NOT NULL,
    creado      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS registros (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vehiculo_id  INTEGER NOT NULL REFERENCES vehiculos(id) ON DELETE CASCADE,
    fecha        TEXT NOT NULL,
    km           INTEGER,
    categoria    TEXT NOT NULL,
    titulo       TEXT NOT NULL,
    detalle      TEXT,
    costo        REAL,
    taller       TEXT,
    prox_km      INTEGER,
    prox_fecha   TEXT,
    hecho_por    TEXT
);
"""


# ---------------------------------------------------------------- base de datos

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Columnas agregadas a vehiculos después de la primera versión.
COLUMNAS_NUEVAS = {
    "carroceria": "TEXT", "color": "TEXT", "version": "TEXT", "equipamiento": "TEXT", "transmision": "TEXT",
    "motor": "TEXT", "cilindrada": "INTEGER", "combustible": "TEXT", "tanque": "REAL", "codigo_pintura": "TEXT",
    "vin": "TEXT", "bujias": "TEXT", "aceite": "TEXT", "aceite_litros": "REAL",
    "refrigerante": "TEXT", "frenos": "TEXT", "neumaticos": "TEXT", "presion_del": "TEXT",
    "presion_tras": "TEXT", "uso": "TEXT", "creado": "TEXT", "share_token": "TEXT",
    "share_costos": "INTEGER DEFAULT 1", "share_adjuntos": "INTEGER DEFAULT 1",
    "imagen_modo": "TEXT", "foto_id": "INTEGER", "km_mes": "INTEGER",
    "foto_x": "INTEGER", "foto_y": "INTEGER", "foto_zoom": "INTEGER", "foto_ajuste": "TEXT",
    "orden": "INTEGER", "transfer_codigo": "TEXT", "transfer_vence": "TEXT",
    "km_manual": "INTEGER", "km_manual_fecha": "TEXT",
}


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.executescript(SCHEMA)
        # Migración: bases creadas antes de existir carrocería y color.
        columnas = {row[1] for row in db.execute("PRAGMA table_info(vehiculos)")}
        for col, tipo in COLUMNAS_NUEVAS.items():
            if col not in columnas:
                db.execute(f"ALTER TABLE vehiculos ADD COLUMN {col} {tipo}")
        if "hecho_por" not in {row[1] for row in db.execute("PRAGMA table_info(registros)")}:
            db.execute("ALTER TABLE registros ADD COLUMN hecho_por TEXT")
            # El viejo "Taller / responsable" pasa a "¿Quién lo hizo?".
            db.execute("UPDATE registros SET hecho_por = CASE WHEN lower(trim(taller)) IN "
                       "('yo', 'yo mismo', 'yo misma', 'por mi', 'por mí', 'propio') "
                       "THEN 'yo' ELSE 'taller' END WHERE COALESCE(trim(taller), '') <> ''")
            db.execute("UPDATE registros SET taller = '' WHERE hecho_por = 'yo'")
        cols_usuarios = {row[1] for row in db.execute("PRAGMA table_info(usuarios)")}
        if "codigo" not in cols_usuarios:
            db.execute("ALTER TABLE usuarios ADD COLUMN codigo TEXT")
        if "cal_token" not in cols_usuarios:
            db.execute("ALTER TABLE usuarios ADD COLUMN cal_token TEXT")
        if "foto" not in cols_usuarios:
            db.execute("ALTER TABLE usuarios ADD COLUMN foto TEXT")
        if "admin" not in cols_usuarios:
            db.execute("ALTER TABLE usuarios ADD COLUMN admin INTEGER NOT NULL DEFAULT 0")
        if "actividad" not in cols_usuarios:
            db.execute("ALTER TABLE usuarios ADD COLUMN actividad TEXT")
        if "datos_garaje" not in cols_usuarios:
            db.execute("ALTER TABLE usuarios ADD COLUMN datos_garaje TEXT NOT NULL DEFAULT 'todos'")
        if "usuario_id" not in columnas:
            db.execute("ALTER TABLE vehiculos ADD COLUMN usuario_id INTEGER "
                       "REFERENCES usuarios(id) ON DELETE CASCADE")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_share_token ON vehiculos(share_token)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cal_token ON usuarios(cal_token)")
        db.execute("CREATE INDEX IF NOT EXISTS ix_sesiones_usuario ON sesiones(usuario_id)")
        db.executescript("""
            CREATE INDEX IF NOT EXISTS ix_vehiculos_usuario ON vehiculos(usuario_id);
            CREATE INDEX IF NOT EXISTS ix_registros_vehiculo ON registros(vehiculo_id, fecha);
            CREATE INDEX IF NOT EXISTS ix_archivos_vehiculo ON archivos(vehiculo_id, registro_id);
        """)
        # Unificar las categorías anteriores sin perder registros ni adjuntos.
        for vieja, nueva in CATEGORIAS_VIEJAS.items():
            db.execute("UPDATE registros SET categoria = ? WHERE categoria = ?", (nueva, vieja))
        # Marcas y modelos escritos a mano ("ford") pasan a su forma del catálogo ("Ford").
        for vid, marca, modelo in db.execute("SELECT id, marca, modelo FROM vehiculos").fetchall():
            m = canon_marca(marca)
            db.execute("UPDATE vehiculos SET marca = ?, modelo = ? WHERE id = ?",
                       (m, canon_modelo(m, modelo), vid))
        # Antes había un solo campo «Versión / fase»: si ahí se anotó la versión de equipamiento
        # (LTZ, Ghia, Highline…), pasa al campo nuevo y la generación queda vacía.
        for vid, marca, modelo, version in db.execute(
                "SELECT id, marca, modelo, version FROM vehiculos WHERE COALESCE(equipamiento, '') = '' "
                "AND COALESCE(version, '') <> ''").fetchall():
            conocida = next((e for e in equipamientos_de(marca, modelo) if e.lower() == version.strip().lower()), None)
            if conocida:
                db.execute("UPDATE vehiculos SET equipamiento = ?, version = NULL WHERE id = ?", (conocida, vid))


init_db()


# ---------------------------------------------------------------- utilidades

@app.url_defaults
def version_estaticos(endpoint, values):
    """Agrega ?v=<fecha del archivo> a los estáticos: el navegador los guarda en
    caché y igual baja la versión nueva apenas cambian."""
    if endpoint == "static" and "filename" in values and "v" not in values:
        try:
            values["v"] = int(os.path.getmtime(os.path.join(app.static_folder, values["filename"])))
        except OSError:
            pass

@app.before_request
def nonce_csp():
    g.csp_nonce = secrets.token_urlsafe(16)


def politica_csp(nonce):
    return "; ".join([
        "default-src 'self'",
        f"script-src 'self' 'nonce-{nonce}' 'wasm-unsafe-eval'",  # wasm: decodificador Draco del visor 3D
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'", "connect-src 'self' blob: data:", "worker-src 'self' blob:", "manifest-src 'self'",
        "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'"])


@app.after_request
def encabezados_de_seguridad(resp):
    h = resp.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("Referrer-Policy", "same-origin")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if HTTPS:
        h.setdefault("Strict-Transport-Security", "max-age=31536000")
    if request.endpoint not in PUBLICAS or g.get("usuario") is not None:
        h.setdefault("X-Robots-Tag", "noindex, nofollow")
    # Los archivos subidos se sirven con su tipo real y nosniff; la CSP de página rompería el visor de PDF.
    if request.endpoint not in ("archivo", "archivo_compartido", "static"):
        h.setdefault("Content-Security-Policy", politica_csp(g.get("csp_nonce", "")))
    # Páginas con datos de la cuenta: que el navegador no las guarde (el botón Atrás tras salir no las muestra).
    if g.get("usuario") is not None and request.endpoint not in ("static", "archivo", "service_worker") \
            and "Cache-Control" not in h:
        h["Cache-Control"] = "no-store"
    return resp


def url_absoluta(endpoint, **valores):
    """URL completa para compartir (links, calendario, Open Graph). En el sitio publicado siempre https,
    aunque el servidor interno de PythonAnywhere atienda por http detrás del proxy."""
    url = url_for(endpoint, _external=True, **valores)
    return url.replace("http://", "https://", 1) if HTTPS else url


app.jinja_env.globals["url_absoluta"] = url_absoluta

# Páginas que pueden aparecer en buscadores; el resto (todo lo que es de una cuenta, links compartidos,
# calendarios y archivos) se marca «noindex».
PUBLICAS = {"index", "login", "registrarse", "recuperar", "terminos", "privacidad", "creditos", "static", "robots", "sitemap"}


RESPALDO_HECHO = {"dia": None}


@app.before_request
def respaldo_diario():
    """Con la primera visita de cada día se copia la base (ver respaldos.py)."""
    hoy = date.today()
    if RESPALDO_HECHO["dia"] == hoy or app.config.get("TESTING_SIN_RESPALDO"):
        return
    RESPALDO_HECHO["dia"] = hoy
    try:
        respaldos.hacer_respaldo(DB_PATH)
    except Exception as e:  # un respaldo fallido nunca debe tirar la página
        app.logger.warning("No se pudo hacer el respaldo diario: %s", e)


@app.before_request
def cargar_usuario():
    """Deja en g.usuario la cuenta de la sesión (None si no hay o ya no existe)."""
    uid, sid = session.get("uid"), session.get("sid")
    g.usuario = None
    if uid is not None:
        if isinstance(sid, str):
            token = hashlib.sha256(sid.encode()).hexdigest()
            g.usuario = get_db().execute(
                "SELECT u.id, u.usuario, u.foto, u.admin, u.actividad, u.datos_garaje FROM usuarios u JOIN sesiones s ON s.usuario_id = u.id "
                "WHERE u.id = ? AND s.token = ? AND s.vence > ?", (uid, token, time.time())).fetchone()
        if g.usuario is None:
            session.clear()


def csrf_token():
    """Token por sesión que llevan todos los formularios: un sitio ajeno no lo conoce,
    así que no puede hacer que tu navegador envíe formularios a GarajeData."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.before_request
def revisar_csrf():
    if request.method != "POST" or app.config.get("CSRF_APAGADO"):
        return
    enviado = request.form.get("csrf") or request.headers.get("X-CSRF-Token") or ""
    esperado = session.get("csrf") or ""
    # Sin token en la sesión no hay nada que comparar: "" == "" no puede valer como permiso.
    if not esperado or not secrets.compare_digest(enviado, esperado):
        abort(400)


@app.before_request
def anotar_actividad():
    """Último día en que se usó cada cuenta (una escritura por día como mucho), para el panel de administración."""
    u = g.get("usuario")
    hoy = date.today().isoformat()
    if u is not None and u["actividad"] != hoy:
        get_db().execute("UPDATE usuarios SET actividad = ? WHERE id = ?", (hoy, u["id"]))
        get_db().commit()


def requiere_admin(view):
    """Solo administradores. A cualquier otro se le responde 404: ni se entera de que la página existe."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.get("usuario") is None or not g.usuario["admin"]:
            abort(404)
        return view(*args, **kwargs)
    return wrapper


def requiere_login(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.usuario is None:
            flash("Ingresá a tu cuenta para continuar.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_globals():
    return {"csrf_token": csrf_token, "lim": limites_fecha(), "csp_nonce": g.get("csp_nonce", ""),
            "can_edit": g.get("usuario") is not None, "usuario": g.get("usuario"),
            "CATEGORIAS": CATEGORIAS, "GRUPOS_CATEGORIAS": GRUPOS_CATEGORIAS, "AYUDA_CATEGORIAS": AYUDA_CATEGORIAS,
            "CARROCERIAS": CARROCERIAS, "COLORES": COLORES, "TRANSMISIONES": TRANSMISIONES,
            "COMBUSTIBLES": COMBUSTIBLES, "FRENOS": FRENOS, "USOS": USOS, "HECHO_POR": HECHO_POR,
            "DOCUMENTOS": DOCUMENTOS, "REPETICIONES": REPETICIONES, "BOVEDA": archivos.BOVEDA,
            "COLOR_DEFAULT": COLOR_DEFAULT,
            "catalogo_js": catalogo_js, "logo_marca": logo_marca, "tema_marca": tema_marca,
            "logo_oscuro": logo_oscuro, "nombre_auto": nombre_auto, "detalle_auto": detalle_auto, "ficha_tecnica": ficha_tecnica,
            "patente_info": patente_info,
            "creditos_modelos": creditos_modelos}


def creditos_modelos():
    """Créditos de los modelos 3D (static/models/modelos.json), sin repetir."""
    try:
        with open(os.path.join(BASE_DIR, "static", "models", "modelos.json"), encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return []
    vistos, creditos = set(), []
    for c in cfg.values():
        if isinstance(c, dict) and c.get("credito") and c["credito"] not in vistos:
            vistos.add(c["credito"])
            creditos.append({"credito": c["credito"], "url": c.get("url")})
    return creditos


def patente_info(patente, carroceria=None):
    """Formato de la patente: ("vieja", "ALF 749") para las de 6 caracteres (1995-2016),
    ("mercosur", "AB 123 CD") para las de 7, o ("otra", tal cual) si no coincide."""
    p = re.sub(r"[^A-Z0-9]", "", (patente or "").upper())
    if carroceria == "moto" and len(p) in (6, 7):
        tipo = "moto-mercosur" if len(p) == 7 else "moto-vieja"
        return tipo, f"{p[:3]}\n{p[3:]}"
    if re.fullmatch(r"[A-Z]{3}\d{3}", p):
        return "vieja", f"{p[:3]} {p[3:]}"
    if re.fullmatch(r"[A-Z]{2}\d{3}[A-Z]{2}", p):
        return "mercosur", f"{p[:2]} {p[2:5]} {p[5:]}"
    return "otra", (patente or "").strip().upper()


def ficha_tecnica(v):
    """Datos técnicos cargados, como pares (etiqueta, valor), sin los vacíos."""
    litros = lambda n: f"{num(n)} L" if n else None  # noqa: E731
    aceite = " · ".join(x for x in (v["aceite"], litros(v["aceite_litros"]) and
                                     f"{litros(v['aceite_litros'])} con filtro") if x)
    pares = [("Cilindrada", f"{v['cilindrada']} cc" if v["carroceria"] == "moto" and v["cilindrada"] else None),
             ("Motor", v["motor"]), ("Combustible", COMBUSTIBLES.get(v["combustible"])),
             ("Tanque", litros(v["tanque"])), ("Código de pintura", v["codigo_pintura"]),
             ("VIN", v["vin"]), ("Aceite", aceite), ("Bujías", v["bujias"]),
             ("Refrigerante", v["refrigerante"]), ("Líquido de frenos", v["frenos"]),
             ("Neumáticos", v["neumaticos"]), ("Presión delantera", v["presion_del"]),
             ("Presión trasera", v["presion_tras"])]
    return [(k, x) for k, x in pares if x]


def nombre_auto(v):
    """Nombre a mostrar: el apodo, o marca + modelo si no tiene."""
    return (v["nombre"] or " ".join(x for x in (v["marca"], v["modelo"], v["version"], v["equipamiento"]) if x)
            or "Mi vehículo")


def detalle_auto(v):
    """Línea corta bajo el nombre: solo lo que el título no dice ya (año, carrocería, caja)."""
    titulo = nombre_auto(v).lower()
    partes = [x for x in (v["marca"], v["modelo"], v["version"], v["equipamiento"]) if x and x.lower() not in titulo]
    partes.append(str(v["anio"]) if v["anio"] else None)
    carroceria = CARROCERIAS.get(v["carroceria"])
    if carroceria and carroceria.lower() not in titulo:
        partes.append(carroceria)
    partes.append(TRANSMISIONES.get(v["transmision"]))
    return " · ".join(p for p in partes if p)


def to_int(value):
    value = (value or "").strip().replace(".", "").replace(",", "")
    # isdigit() acepta cosas como «²» o «١٢٣» que int() no entiende; y un número enorme no entra en SQLite.
    if not (value.isascii() and value.isdigit()) or len(value) > 12:
        return None
    return int(value)


def to_float(value):
    value = (value or "").strip().replace("$", "").replace(" ", "")
    if not value:
        return None
    # Formato argentino: el punto separa miles y la coma los decimales (1.234,56).
    value = value.replace(".", "").replace(",", ".")
    try:
        n = float(value)
    except ValueError:
        return None
    # nan, inf o cifras absurdas romperían los totales y los gráficos
    return n if math.isfinite(n) and abs(n) < 1e12 else None


@app.template_filter("num")
def num(n):
    """Valor para precargar un campo numérico: 21000 -> "21.000", 1234.5 -> "1.234,50".
    Vacío si no hay número (None o un campo que el formulario nuevo todavía no tiene)."""
    if not isinstance(n, (int, float)) or isinstance(n, bool):
        return ""
    return plata(n)[2:]


@app.template_filter("miles")
def miles(n):
    if n is None:
        return "—"
    return f"{int(n):,}".replace(",", ".")


@app.template_filter("plata")
def plata(n):
    if n is None:
        return "—"
    entero, dec = f"{n:,.2f}".split(".")
    entero = entero.replace(",", ".")
    return f"$ {entero}" if dec == "00" else f"$ {entero},{dec}"


@app.template_filter("fecha")
def fecha(iso):
    if not iso:
        return "—"
    try:
        return date.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return iso


def get_vehiculo(vid):
    """Vehículo de la cuenta actual; 404 si no existe o es de otra persona."""
    v = get_db().execute("SELECT * FROM vehiculos WHERE id = ? AND usuario_id = ?",
                         (vid, g.usuario["id"])).fetchone()
    if v is None:
        abort(404)
    return v


def km_actual(v):
    row = get_db().execute(
        "SELECT MAX(km) FROM registros WHERE vehiculo_id = ?", (v["id"],)
    ).fetchone()
    return max(v["km_inicial"] or 0, row[0] or 0, v["km_manual"] or 0)


def progreso(r, km_hoy, hoy):
    """Qué tanto se avanzó desde el trabajo hasta el próximo control (0 a 1),
    por kilómetros o por fecha, lo que esté más cerca."""
    valores = []
    if r["prox_km"] and r["km"] is not None and r["prox_km"] > r["km"]:
        valores.append((km_hoy - r["km"]) / (r["prox_km"] - r["km"]))
    try:
        desde, hasta = date.fromisoformat(r["fecha"]), date.fromisoformat(r["prox_fecha"] or "")
        if hasta > desde:
            valores.append((hoy - desde).days / (hasta - desde).days)
    except ValueError:
        pass
    return min(1.0, max([0.0, *valores]))


def calcular_recordatorios(vid, km_hoy):
    """Para cada trabajo (por título), toma el registro más reciente y, si tiene
    un próximo control cargado, indica si está vencido, cerca o al día."""
    rows = get_db().execute(
        "SELECT * FROM registros WHERE vehiculo_id = ? "
        "ORDER BY fecha DESC, km DESC, id DESC", (vid,)
    ).fetchall()
    hoy = date.today()
    vistos, recordatorios = set(), []
    for r in rows:
        clave = r["titulo"].strip().lower()
        if clave in vistos:
            continue
        vistos.add(clave)
        if not (r["prox_km"] or r["prox_fecha"]):
            continue
        faltan_km = r["prox_km"] - km_hoy if r["prox_km"] else None
        faltan_dias = None
        if r["prox_fecha"]:
            try:
                faltan_dias = (date.fromisoformat(r["prox_fecha"]) - hoy).days
            except ValueError:
                pass
        if (faltan_km is not None and faltan_km <= 0) or \
           (faltan_dias is not None and faltan_dias <= 0):
            estado = "vencido"
        elif (faltan_km is not None and faltan_km <= 1000) or \
             (faltan_dias is not None and faltan_dias <= 30):
            estado = "pronto"
        else:
            estado = "ok"
        recordatorios.append({"registro": r, "estado": estado, "faltan_km": faltan_km,
                              "faltan_dias": faltan_dias,
                              "progreso": 1.0 if estado == "vencido" else progreso(r, km_hoy, hoy)})
    for p in get_db().execute("SELECT * FROM pendientes WHERE vehiculo_id = ? ORDER BY fecha, km, id", (vid,)):
        faltan_km = p["km"] - km_hoy if p["km"] else None
        faltan_dias = None
        if p["fecha"]:
            try:
                faltan_dias = (date.fromisoformat(p["fecha"]) - hoy).days
            except ValueError:
                pass
        if (faltan_km is not None and faltan_km <= 0) or (faltan_dias is not None and faltan_dias < 0):
            estado = "vencido"
        elif (faltan_km is not None and faltan_km <= 1000) or (faltan_dias is not None and faltan_dias <= 30):
            estado = "pronto"
        else:
            estado = "ok"
        # Mismo formato que un registro con «próximo control», para que lo usen igual todas las vistas.
        reg = {"id": None, "titulo": p["titulo"], "prox_km": p["km"], "prox_fecha": p["fecha"],
               "categoria": p["categoria"], "detalle": p["detalle"]}
        recordatorios.append({"registro": reg, "pendiente": p["id"], "estado": estado, "faltan_km": faltan_km,
                              "faltan_dias": faltan_dias, "progreso": 1.0 if estado == "vencido" else 0.0})
    orden = {"vencido": 0, "pronto": 1, "ok": 2}
    recordatorios.sort(key=lambda x: orden[x["estado"]])
    return recordatorios


def limitar(valor, minimo, maximo, defecto):
    n = to_int(valor)
    return min(maximo, max(minimo, n)) if n is not None else defecto


def datos_foto_form():
    """Imagen del auto: modo (3D o foto), posición (0-100 %), zoom (100-300 %) y si la
    foto llena el marco o se ve entera."""
    f = request.form
    return {
        "imagen_modo": "foto" if f.get("imagen_modo") == "foto" else "3d",
        "foto_x": limitar(f.get("foto_x"), 0, 100, 50),
        "foto_y": limitar(f.get("foto_y"), 0, 100, 50),
        "foto_zoom": limitar(f.get("foto_zoom"), 100, 300, 100),
        "foto_ajuste": "completa" if f.get("foto_ajuste") == "completa" else "cubrir",
    }


def datos_vehiculo_form():
    f = request.form
    color = f.get("color", "").strip().lower()
    if not re.fullmatch(r"#[0-9a-f]{6}", color):
        color = COLOR_DEFAULT
    carroceria = f.get("carroceria")
    if f.get("tipo_vehiculo") == "moto":
        carroceria = "moto"
    elif f.get("tipo_vehiculo") == "auto" and carroceria == "moto":
        carroceria = "sedan"
    cilindrada = to_int(f.get("cilindrada"))
    marca = canon_marca(f.get("marca"))
    transmision = f.get("transmision")
    uso = f.get("uso") if carroceria != "moto" and f.get("calcular_uso") and f.get("uso") in USOS else None
    km_mes = to_int(f.get("km_mes"))
    if uso == "personalizado" and not (km_mes and 0 < km_mes <= KM_MES_MAX):
        flash(f"Para el plan de mantenimiento personalizado poné los km por mes (entre 1 y {KM_MES_MAX:,}"
              .replace(",", ".") + ").", "error")
        uso = None
    return {
        "version": texto("version", 60),
        "equipamiento": texto("equipamiento", 40),
        "transmision": transmision if transmision in TRANSMISIONES else None,
        "carroceria": carroceria if carroceria in CARROCERIAS else "sedan",
        "color": color,
        "nombre": texto("nombre", 60),
        "marca": marca,
        "modelo": canon_modelo(marca, f.get("modelo")),
        "anio": to_int(f.get("anio")),
        "patente": patente_info(f.get("patente"))[1],
        "km_inicial": to_int(f.get("km_inicial")),
        "notas": texto("notas", 4000),
        "motor": texto("motor", 60),
        "cilindrada": cilindrada if carroceria == "moto" and cilindrada and 1 <= cilindrada <= 10000 else None,
        "combustible": f.get("combustible") if f.get("combustible") in COMBUSTIBLES else None,
        "tanque": to_float(f.get("tanque")),
        "codigo_pintura": texto("codigo_pintura", 30),
        "vin": re.sub(r"[^A-Z0-9]", "", texto("vin", 40).upper())[:17],
        "bujias": texto("bujias", 60),
        "aceite": texto("aceite", 60),
        "aceite_litros": to_float(f.get("aceite_litros")),
        "refrigerante": texto("refrigerante", 60),
        "frenos": f.get("frenos") if f.get("frenos") in FRENOS else None,
        "neumaticos": texto("neumaticos", 60),
        "presion_del": texto("presion_del", 20),
        "presion_tras": texto("presion_tras", 20),
        **datos_foto_form(),
        # El plan de mantenimiento es opcional: solo con la casilla tildada.
        "uso": uso,
        "km_mes": km_mes if uso == "personalizado" else None,
    }


def to_fecha(value, minimo=None, maximo=None):
    """Fecha ISO válida (AAAA-MM-DD) dentro del rango permitido, o None.
    Por defecto: desde 1980 hasta dentro de 30 años (un año 0001 no tiene sentido)."""
    try:
        d = date.fromisoformat((value or "").strip())
    except ValueError:
        return None
    minimo = minimo or date(1980, 1, 1)
    maximo = maximo or date.today() + timedelta(days=365 * 30)
    return d.isoformat() if minimo <= d <= maximo else None


def limites_fecha():
    """Rangos de fecha para los formularios (también se usan como min/max de los campos)."""
    hoy = date.today()
    return {"hoy": hoy.isoformat(), "inicio_anio": date(hoy.year, 1, 1).isoformat(),
            "hace_un_anio": (hoy - timedelta(days=365)).isoformat(),
            "en_30_anios": (hoy + timedelta(days=365 * 30)).isoformat(),
            "desde": "1980-01-01"}


def texto(campo, largo):
    return request.form.get(campo, "").strip()[:largo]


def categoria_valida(categoria):
    """La categoría tal cual si existe, la nueva si es una de las que se fusionaron, y si no «otro»."""
    categoria = CATEGORIAS_VIEJAS.get(categoria, categoria)
    return categoria if categoria in CATEGORIAS else "otro"


def datos_registro_form():
    f = request.form
    hecho_por = f.get("hecho_por") if f.get("hecho_por") in HECHO_POR else None
    return {
        # el trabajo ya se hizo: no puede ser de una fecha futura
        "fecha": to_fecha(f.get("fecha"), maximo=date.today()) or date.today().isoformat(),
        "km": to_int(f.get("km")),
        "categoria": categoria_valida(f.get("categoria")),
        "titulo": texto("titulo", 120),
        "detalle": texto("detalle", 4000),
        "costo": to_float(f.get("costo")),
        "hecho_por": hecho_por,
        # Nombre del taller o de quien lo hizo; "hecho por mí" no lleva nombre.
        "taller": texto("taller", 120) if hecho_por in ("taller", "otro") else "",
        "prox_km": to_int(f.get("prox_km")),
        # También se conserva un control vencido de años anteriores al editar el historial.
        "prox_fecha": to_fecha(f.get("prox_fecha")),
    }


# ---------------------------------------------------------------- rutas: cuentas

# Intentos fallidos de ingreso por usuario: {usuario: [momentos]}. Frena a quien
# prueba contraseñas al azar (5 intentos cada 10 minutos).
INTENTOS = {}
MAX_INTENTOS, VENTANA = 5, 600
# Límites del ingreso: por usuario desde la misma conexión (5), por usuario desde cualquier lado (25, frena
# la prueba de contraseñas repartida entre muchas IP) y por conexión (40, frena el barrido de usuarios).
# Así un tercero no puede dejar fuera a un usuario real con solo equivocarse 5 veces desde otra conexión.
LIMITES_INGRESO = ((5, "{n}|{ip}"), (25, "{n}|*"), (40, "*|{ip}"))


def bloqueado(nombre, maximo=MAX_INTENTOS):
    ahora = time.time()
    if len(INTENTOS) > 20_000:  # nadie puede llenar la memoria con claves inventadas
        for k in [k for k, v in INTENTOS.items() if not v or ahora - v[-1] >= VENTANA]:
            del INTENTOS[k]
    INTENTOS[nombre] = [t for t in INTENTOS.get(nombre, []) if ahora - t < VENTANA]
    return len(INTENTOS[nombre]) >= maximo


def ingreso_bloqueado(nombre):
    n, ip = nombre.lower(), ip_cliente()
    return any(bloqueado(plantilla.format(n=n, ip=ip), maximo) for maximo, plantilla in LIMITES_INGRESO)


def ingreso_fallido(nombre):
    n, ip = nombre.lower(), ip_cliente()
    for _, plantilla in LIMITES_INGRESO:
        INTENTOS.setdefault(plantilla.format(n=n, ip=ip), []).append(time.time())


def ingreso_ok(nombre):
    INTENTOS.pop(f"{nombre.lower()}|{ip_cliente()}", None)


# Para que probar un usuario que no existe tarde lo mismo que probar uno real.
CLAVE_FALSA = generate_password_hash("clave-que-nadie-usa")


# Límite de cuentas nuevas: por IP (contra robots) y en total (el plan gratis tiene 512 MB).
ALTAS_IP = {}
MAX_ALTAS_IP, VENTANA_ALTAS = 3, 24 * 3600
MAX_USUARIOS = int(os.environ.get("MAX_USUARIOS", "300"))


def ip_cliente():
    # En PythonAnywhere la app está detrás de un proxy que pasa la IP real en X-Real-IP.
    return (request.headers.get("X-Real-IP") or request.remote_addr or "?")[:64]


def motivo_sin_altas():
    """Texto del error si ahora no se pueden crear cuentas desde esta IP; None si se puede."""
    ahora, ip = time.time(), ip_cliente()
    ALTAS_IP[ip] = [t for t in ALTAS_IP.get(ip, []) if ahora - t < VENTANA_ALTAS]
    if len(ALTAS_IP[ip]) >= MAX_ALTAS_IP:
        return "Se crearon demasiadas cuentas desde esta conexión. Probá de nuevo mañana."
    if get_db().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] >= MAX_USUARIOS:
        return "Por ahora no hay lugar para cuentas nuevas. Probá más adelante."
    return None


def destino_seguro():
    destino = request.args.get("next", "")
    # Solo rutas internas: "//otro-sitio.com" también empieza con "/".
    interno = destino.startswith("/") and not destino.startswith(("//", "/\\"))
    return destino if interno else url_for("index")


def iniciar_sesion(uid):
    session.clear()
    session["uid"] = uid
    sid = secrets.token_urlsafe(32)
    db = get_db()
    db.execute("DELETE FROM sesiones WHERE vence <= ?", (time.time(),))
    db.execute("INSERT INTO sesiones (token, usuario_id, vence) VALUES (?, ?, ?)",
               (hashlib.sha256(sid.encode()).hexdigest(), uid,
                time.time() + app.permanent_session_lifetime.total_seconds()))
    db.commit()
    session["sid"] = sid
    session.permanent = True


def invalidar_sesiones(uid):
    """Cambiar o recuperar la contraseña cierra todas las sesiones anteriores."""
    get_db().execute("DELETE FROM sesiones WHERE usuario_id = ?", (uid,))


# Código de recuperación: reemplaza al email para recuperar la cuenta, así no se
# guarda ningún dato personal. Se muestra una sola vez y en la base queda solo
# su hash, igual que la contraseña. Sin letras que se confunden (0/O, 1/I/L).
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def normalizar_codigo(codigo):
    return re.sub(r"[^A-Z0-9]", "", (codigo or "").upper())


def nuevo_codigo(uid):
    """Genera un código nuevo para la cuenta, guarda su hash y lo deja para mostrar."""
    crudo = "".join(secrets.choice(ALFABETO) for _ in range(16))
    get_db().execute("UPDATE usuarios SET codigo = ? WHERE id = ?",
                     (generate_password_hash(crudo), uid))
    get_db().commit()
    session["codigo_nuevo"] = "-".join(crudo[i:i + 4] for i in range(0, 16, 4))


def validar_clave(clave, clave2):
    if len(clave) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if len(clave) > 200:
        return "La contraseña es demasiado larga."
    if clave != clave2:
        return "Las contraseñas no coinciden."
    return None


# ---------------------------------------------------------------- rutas: vehículos

CAMPOS_VEHICULO = ["imagen_modo", "km_mes", "foto_x", "foto_y", "foto_zoom", "foto_ajuste", "nombre", "marca", "modelo", "version", "equipamiento", "anio", "patente", "km_inicial", "notas",
                   "carroceria", "color", "transmision", "motor", "cilindrada", "combustible", "tanque",
                   "codigo_pintura", "vin", "bujias", "aceite", "aceite_litros", "refrigerante",
                   "frenos", "neumaticos", "presion_del", "presion_tras", "uso"]


def registros_de(vid):
    return get_db().execute("SELECT * FROM registros WHERE vehiculo_id = ? "
                            "ORDER BY fecha DESC, km DESC, id DESC", (vid,)).fetchall()


def documentos_de(vid):
    return get_db().execute("SELECT * FROM documentos WHERE vehiculo_id = ?", (vid,)).fetchall()


def adjuntos_por_registro(vid):
    salida = {}
    for a in get_db().execute("SELECT * FROM archivos WHERE vehiculo_id = ? AND registro_id IS NOT NULL "
                              "ORDER BY id", (vid,)):
        salida.setdefault(a["registro_id"], []).append(a)
    return salida


def avisos(v, registros=None):
    """Todo lo que hay que mirar de un vehículo: controles cargados a mano, plan
    de mantenimiento estimado y vencimientos de documentación."""
    registros = registros if registros is not None else registros_de(v["id"])
    km_hoy = max(km_actual(v), km_estimado(v, registros)) if v["uso"] else km_actual(v)
    return {"km_hoy": km_hoy,
            "recordatorios": calcular_recordatorios(v["id"], km_hoy),
            "plan": plan_mantenimiento(v, registros),
            "documentos": vencimientos(documentos_de(v["id"]))}


def contar_avisos(a):
    estados = ([r["estado"] for r in a["recordatorios"]] + [p["estado"] for p in a["plan"]]
               + [d["estado"] for d in a["documentos"]])
    return {"vencido": estados.count("vencido"), "pronto": estados.count("pronto")}


def guardar_portada(vid):
    """Foto propia del auto (en lugar del modelo 3D): sube, reemplaza o quita la
    foto y deja el modo coherente (sin foto no se puede mostrar la foto)."""
    db = get_db()
    v = db.execute("SELECT * FROM vehiculos WHERE id = ?", (vid,)).fetchone()
    previas = db.execute("SELECT * FROM archivos WHERE vehiculo_id = ? AND categoria = 'portada'",
                         (vid,)).fetchall()
    nueva = request.files.get("foto")
    foto_id = v["foto_id"]

    def quitar_previas():
        for a in previas:
            db.execute("DELETE FROM archivos WHERE id = ?", (a["id"],))
        archivos.borrar([a["archivo"] for a in previas])

    if request.form.get("quitar_foto"):
        quitar_previas()
        foto_id = None
    if nueva and nueva.filename:
        try:
            en_disco, mime, peso, nombre = archivos.guardar(nueva, espacio_usado(), solo_imagen=True)
        except ValueError as e:
            flash(str(e), "error")
        else:
            quitar_previas()
            foto_id = db.execute(
                "INSERT INTO archivos (vehiculo_id, registro_id, categoria, nombre, archivo, mime, bytes, creado) "
                "VALUES (?, NULL, 'portada', ?, ?, ?, ?, ?)",
                (vid, nombre, en_disco, mime, peso, datetime.now().isoformat(timespec="seconds"))).lastrowid
    modo = v["imagen_modo"]
    if modo == "foto" and not foto_id:
        modo = "3d"
        flash("Para mostrar tu foto primero elegí una. Por ahora se ve el modelo 3D.", "error")
    db.execute("UPDATE vehiculos SET foto_id = ?, imagen_modo = ? WHERE id = ?", (foto_id, modo, vid))
    db.commit()


def proximo_control(v, a):
    """El control de mantenimiento que viene antes (cargado a mano o estimado por el
    plan de uso), para la tarjeta del auto. Devuelve None si no hay ninguno programado."""
    kpm = km_por_mes(v) or 1250
    orden = {"vencido": 0, "pronto": 1, "ok": 2}
    candidatos = []  # (estado, días aproximados, título, detalle)

    def km_a_dias(km):
        return km / kpm * 30.44

    for rec in a["recordatorios"]:
        dias = [d for d in (rec["faltan_dias"],
                            km_a_dias(rec["faltan_km"]) if rec["faltan_km"] is not None else None) if d is not None]
        if rec["estado"] == "vencido":
            detalle = "Vencido"
        else:
            partes = []
            if rec["faltan_km"] is not None:
                partes.append(f"en {miles(rec['faltan_km'])} km")
            elif rec["faltan_dias"] is not None:
                partes.append(f"en {rec['faltan_dias']} días")
            detalle = " · ".join(partes)
        candidatos.append((rec["estado"], min(dias) if dias else 9999, rec["registro"]["titulo"], detalle))
    for p in a["plan"]:
        if p["estado"] == "sin_dato":
            continue
        if p["estado"] == "vencido":
            detalle = "Ya toca"
        elif p["faltan_km"] is not None:
            detalle = f"en ≈ {miles(p['faltan_km'])} km"
        else:
            detalle = f"en ≈ {p['dias']} días"
        candidatos.append((p["estado"], p["dias"], p["nombre"], detalle))
    if not candidatos:
        return None
    estado, _, titulo, detalle = min(candidatos, key=lambda c: (orden[c[0]], c[1]))
    return {"estado": estado, "titulo": titulo, "detalle": detalle}


def lista_avisos(v, a, con_nombre=False):
    """Avisos urgentes (vencidos o por vencer) de un vehículo, para el cartel lateral."""
    nombre = nombre_auto(v)
    url = url_for("vehiculo", vid=v["id"])
    salida = []

    def agregar(clave, titulo, detalle, estado, destino=None):
        salida.append({"clave": f"{v['id']}:{clave}", "titulo": titulo, "detalle": detalle,
                       "estado": estado, "url": destino or url, "auto": nombre if con_nombre else None})

    for rec in a["recordatorios"]:
        if rec["estado"] == "ok":
            continue
        partes = []
        if rec["estado"] == "vencido":
            partes.append("Vencido")
        else:
            if rec["faltan_km"] is not None:
                partes.append(f"faltan {miles(rec['faltan_km'])} km")
            if rec["faltan_dias"] is not None:
                partes.append(f"{rec['faltan_dias']} días")
        destino = (url_for("vehiculo", vid=v["id"], _anchor="controles") if rec.get("pendiente")
                   else url_for("vehiculo", vid=v["id"], _anchor="registro-" + str(rec["registro"]["id"])))
        agregar(("pend:" + str(rec["pendiente"])) if rec.get("pendiente") else "rec:" + rec["registro"]["titulo"].strip().lower(),
                rec["registro"]["titulo"], " · ".join(partes), rec["estado"], destino)
    for p in a["plan"]:
        if p["estado"] in ("vencido", "pronto"):
            detalle = "Ya toca" if p["estado"] == "vencido" else \
                f"≈ {fecha(p['fecha'])}" + (f" · {miles(p['faltan_km'])} km" if p["faltan_km"] is not None else "")
            agregar("plan:" + p["clave"], p["nombre"] + " (estimado)", detalle, p["estado"],
                    url_for("registro_nuevo", vid=v["id"], titulo=p["nombre"]))
    for d in a["documentos"]:
        if d["estado"] not in ("vencido", "pronto") or d["dias"] is None:
            continue
        detalle = (f"Venció hace {-d['dias']} {'día' if d['dias'] == -1 else 'días'}" if d["dias"] < 0
                   else "Vence hoy" if d["dias"] == 0
                   else f"Faltan {d['dias']} {'día' if d['dias'] == 1 else 'días'}")
        agregar("doc:" + d["doc"]["tipo"], d["nombre"], detalle, d["estado"], url_for("documentos", vid=v["id"]))
    salida.sort(key=lambda x: x["estado"] != "vencido")
    return salida


def celda_csv(valor):
    """Evita que Excel interprete como fórmula un texto que empieza con = + - @."""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@"):
        return "'" + valor
    return valor


def quien(r):
    """Quién hizo el trabajo, en una línea: "Taller Juan", "Hecho por mí"…"""
    if r["hecho_por"] == "yo":
        return "Hecho por mí"
    if r["hecho_por"] == "otro":
        return r["taller"] or "Otro"
    return r["taller"] or ("Taller / mecánico" if r["hecho_por"] == "taller" else "")


app.jinja_env.globals["quien"] = quien


# ---------------------------------------------------------------- rutas: archivos

def espacio_usado():
    return get_db().execute(
        "SELECT COALESCE(SUM(a.bytes), 0) FROM archivos a JOIN vehiculos v ON v.id = a.vehiculo_id "
        "WHERE v.usuario_id = ?", (g.usuario["id"],)).fetchone()[0]


def subir_archivos(vid, registro_id=None, categoria=None):
    """Guarda los archivos del campo "archivos" del formulario. Los que no se
    pueden guardar se avisan con un mensaje y el resto sigue."""
    usados = espacio_usado()
    subidos = 0
    for f in request.files.getlist("archivos"):
        if not f or not f.filename:
            continue
        try:
            en_disco, mime, peso, nombre = archivos.guardar(f, usados)
        except ValueError as e:
            flash(str(e), "error")
            continue
        usados += peso
        get_db().execute(
            "INSERT INTO archivos (vehiculo_id, registro_id, categoria, nombre, archivo, mime, bytes, creado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (vid, registro_id, categoria, nombre, en_disco, mime, peso,
             datetime.now().isoformat(timespec="seconds")))
        subidos += 1
    get_db().commit()
    return subidos


def enviar_archivo(a):
    try:
        resp = send_file(archivos.ruta(a["archivo"]), mimetype=a["mime"], download_name=a["nombre"],
                         as_attachment=request.args.get("descargar") == "1", max_age=0)
    except FileNotFoundError:
        abort(404)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "private, no-cache"
    return resp


def get_archivo(aid):
    a = get_db().execute("SELECT * FROM archivos WHERE id = ?", (aid,)).fetchone()
    if a is None:
        abort(404)
    get_vehiculo(a["vehiculo_id"])
    return a


# ---------------------------------------------------------------- rutas: libro de servicio y compartir

def datos_libro(v, mostrar_costos=True, mostrar_adjuntos=True):
    registros = get_db().execute("SELECT * FROM registros WHERE vehiculo_id = ? "
                                 "ORDER BY fecha, km, id", (v["id"],)).fetchall()
    total = sum(r["costo"] or 0 for r in registros)
    fechas = [r["fecha"] for r in registros]
    return {"v": v, "registros": registros, "km_hoy": km_actual(v), "total": total,
            "desde": min(fechas) if fechas else None, "hasta": max(fechas) if fechas else None,
            "por_categoria": {c: sum(1 for r in registros if r["categoria"] == c) for c in CATEGORIAS},
            "adjuntos": adjuntos_por_registro(v["id"]) if mostrar_adjuntos else {},
            "mostrar_costos": mostrar_costos, "hoy": date.today().isoformat()}


def vehiculo_compartido(token):
    v = get_db().execute("SELECT * FROM vehiculos WHERE share_token = ?", (token,)).fetchone()
    if v is None:
        abort(404)
    return v


# ---------------------------------------------------------------- rutas: registros

def guardar_pendiente(v):
    """«Lo tengo que hacer»: un trabajo a futuro (no va a la bitácora hasta que se hace)."""
    f = request.form
    titulo = (f.get("titulo") or "").strip()[:120]
    fecha_p = to_fecha(f.get("pend_fecha"), minimo=date.today())
    km_p = to_int(f.get("pend_km"))
    error = ("Indicá qué hay que hacer." if not titulo
             else "La fecha del pendiente tiene que ser de hoy en adelante." if f.get("pend_fecha") and not fecha_p
             else "Poné para cuándo (una fecha de hoy en adelante) o a qué kilometraje." if not (fecha_p or km_p)
             else None)
    if error:
        flash(error, "error")
        r = {"titulo": titulo, "categoria": categoria_valida(f.get("categoria")), "pend_fecha": f.get("pend_fecha"),
             "pend_km": km_p, "detalle": f.get("detalle"), "fecha": date.today().isoformat(), "km": km_actual(v) or None}
        return render_template("registro_form.html", v=v, r=r, adjuntos=[], modo="pendiente")
    get_db().execute("INSERT INTO pendientes (vehiculo_id, titulo, categoria, fecha, km, detalle, creado) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (v["id"], titulo, categoria_valida(f.get("categoria")), fecha_p, km_p,
                      (f.get("detalle") or "").strip()[:4000] or None, datetime.now().isoformat(timespec="seconds")))
    get_db().commit()
    flash("Anotado como pendiente. Te lo recordamos en la ficha, el calendario y los avisos.", "ok")
    return redirect(url_for("vehiculo", vid=v["id"], _anchor="controles"))


def get_pendiente(pid):
    """Pendiente de un vehículo del usuario; 404 si no existe o es de otra cuenta."""
    p = get_db().execute("SELECT p.* FROM pendientes p JOIN vehiculos v ON v.id = p.vehiculo_id "
                         "WHERE p.id = ? AND v.usuario_id = ?", (pid, g.usuario["id"])).fetchone()
    if p is None:
        abort(404)
    return p


def guardar_registro(v, rid=None):
    """Alta o edición de un registro con sus fotos y facturas."""
    if rid is None and request.form.get("modo") == "pendiente":
        return guardar_pendiente(v)
    d = datos_registro_form()
    error = None
    if not d["titulo"]:
        error = "Indicá qué trabajo se hizo."
    elif "fecha" in request.form and not to_fecha(request.form.get("fecha"), maximo=date.today()):
        error = "La fecha del trabajo tiene que ser válida, desde 1980 hasta hoy."
    elif request.form.get("prox_fecha") and not d["prox_fecha"]:
        error = "La fecha del próximo control no es válida o está fuera del rango permitido."
    if error:
        flash(error, "error")
        return render_template("registro_form.html", v=v,
                               r={**d, "fecha": request.form.get("fecha", d["fecha"]),
                                  "prox_fecha": request.form.get("prox_fecha", d["prox_fecha"]),
                                  "id": rid, "pendiente": to_int(request.form.get("pendiente"))},
                               adjuntos=adjuntos_por_registro(v["id"]).get(rid, []))
    db = get_db()
    if rid is None:
        d["vehiculo_id"] = v["id"]
        rid = db.execute(
            "INSERT INTO registros (vehiculo_id, fecha, km, categoria, titulo, detalle, costo, "
            "taller, hecho_por, prox_km, prox_fecha) VALUES (:vehiculo_id, :fecha, :km, :categoria, "
            ":titulo, :detalle, :costo, :taller, :hecho_por, :prox_km, :prox_fecha)", d).lastrowid
        # Si venía de «Ya lo hice» en un pendiente, ese pendiente se cierra.
        pid = to_int(request.form.get("pendiente"))
        if pid:
            db.execute("DELETE FROM pendientes WHERE id = ? AND vehiculo_id = ?", (pid, v["id"]))
        flash("Registro agregado a la bitácora.", "ok")
    else:
        d["id"] = rid
        db.execute(
            "UPDATE registros SET fecha=:fecha, km=:km, categoria=:categoria, titulo=:titulo, "
            "detalle=:detalle, costo=:costo, taller=:taller, hecho_por=:hecho_por, prox_km=:prox_km, "
            "prox_fecha=:prox_fecha WHERE id=:id", d)
        quitar = [to_int(x) for x in request.form.getlist("quitar")]
        borrar = [a for a in adjuntos_por_registro(v["id"]).get(rid, []) if a["id"] in quitar]
        for a in borrar:
            db.execute("DELETE FROM archivos WHERE id = ?", (a["id"],))
        archivos.borrar([a["archivo"] for a in borrar])
        flash("Registro actualizado.", "ok")
    db.commit()
    subir_archivos(v["id"], registro_id=rid)
    return redirect(url_for("vehiculo", vid=v["id"]))


@app.errorhandler(404)
def no_encontrado(e):
    return render_template("404.html"), 404


@app.errorhandler(OverflowError)
def numero_enorme(e):
    # /vehiculo/99999999999999999999: no es un id posible, es lo mismo que uno que no existe
    return render_template("404.html"), 404


@app.errorhandler(500)
def error_interno(e):
    return render_template("404.html", codigo="Ups", titulo="Algo salió mal",
                           mensaje="Tuvimos un problema con esta página. Probá de nuevo en un momento; "
                                   "si sigue pasando, avisá al contacto de la página de Privacidad."), 500


@app.errorhandler(400)
def pedido_invalido(e):
    return render_template("404.html", codigo="Ups", titulo="La página quedó vieja",
                           mensaje="El formulario venció o se abrió desde otro sitio. "
                                   "Volvé atrás, recargá la página y probá de nuevo."), 400


@app.errorhandler(413)
def muy_grande(e):
    return render_template("404.html", codigo="Uy", titulo="Archivos demasiado pesados",
                           mensaje="Lo que intentaste subir pasa los 45 MB en total. "
                                   "Probá con menos archivos o más livianos."), 413
