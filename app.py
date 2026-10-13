"""GarajeData — bitácora del automotor.

App Flask + SQLite para llevar el registro de controles, cambios de fluidos,
piezas, reparaciones y modificaciones de uno o más vehículos.
"""
import csv
import io
import json
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
from catalogo import canon_marca, canon_modelo, catalogo_js, logo_marca, logo_oscuro
from mantenimiento import (KM_MES_MAX, DOCUMENTOS, REPETICION_SUGERIDA, REPETICIONES, USOS, km_estimado,
                           plan_mantenimiento, promedio_medido, sumar_meses, vencimientos)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "bitacora.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambiame-por-una-clave-secreta")
# Lax: el navegador no manda la sesión en formularios enviados desde otros sitios.
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  PERMANENT_SESSION_LIFETIME=timedelta(days=60),
                  MAX_CONTENT_LENGTH=45 * 1024 * 1024)

CATEGORIAS = {
    "control": "Control / Service",
    "fluidos": "Cambio de fluidos",
    "piezas": "Cambio de piezas",
    "accesorios": "Cambio de accesorios",
    "reparacion": "Reparación",
    "modificacion": "Modificación",
    "otro": "Otro",
}

TRANSMISIONES = {"manual": "Manual", "automatica": "Automática"}
COMBUSTIBLES = {"nafta": "Nafta", "diesel": "Diésel", "gnc": "GNC + nafta",
                "hibrido": "Híbrido", "electrico": "Eléctrico"}
FRENOS = ["DOT 3", "DOT 4", "DOT 5.1"]
HECHO_POR = {"taller": "Taller / mecánico", "yo": "Hecho por mí", "otro": "Otro"}

CARROCERIAS = {
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
CREATE TABLE IF NOT EXISTS documentos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos(id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL,
    vence       TEXT,
    cada_meses  INTEGER,
    detalle     TEXT,
    UNIQUE (vehiculo_id, tipo)
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
    "carroceria": "TEXT", "color": "TEXT", "version": "TEXT", "transmision": "TEXT",
    "motor": "TEXT", "combustible": "TEXT", "tanque": "REAL", "codigo_pintura": "TEXT",
    "vin": "TEXT", "bujias": "TEXT", "aceite": "TEXT", "aceite_litros": "REAL",
    "refrigerante": "TEXT", "frenos": "TEXT", "neumaticos": "TEXT", "presion_del": "TEXT",
    "presion_tras": "TEXT", "uso": "TEXT", "creado": "TEXT", "share_token": "TEXT",
    "share_costos": "INTEGER DEFAULT 1", "share_adjuntos": "INTEGER DEFAULT 1",
    "imagen_modo": "TEXT", "foto_id": "INTEGER", "km_mes": "INTEGER",
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
        if "codigo" not in {row[1] for row in db.execute("PRAGMA table_info(usuarios)")}:
            db.execute("ALTER TABLE usuarios ADD COLUMN codigo TEXT")
        if "usuario_id" not in columnas:
            db.execute("ALTER TABLE vehiculos ADD COLUMN usuario_id INTEGER "
                       "REFERENCES usuarios(id) ON DELETE CASCADE")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_share_token ON vehiculos(share_token)")
        db.executescript("""
            CREATE INDEX IF NOT EXISTS ix_vehiculos_usuario ON vehiculos(usuario_id);
            CREATE INDEX IF NOT EXISTS ix_registros_vehiculo ON registros(vehiculo_id, fecha);
            CREATE INDEX IF NOT EXISTS ix_archivos_vehiculo ON archivos(vehiculo_id, registro_id);
        """)
        # Marcas y modelos escritos a mano ("ford") pasan a su forma del catálogo ("Ford").
        for vid, marca, modelo in db.execute("SELECT id, marca, modelo FROM vehiculos").fetchall():
            m = canon_marca(marca)
            db.execute("UPDATE vehiculos SET marca = ?, modelo = ? WHERE id = ?",
                       (m, canon_modelo(m, modelo), vid))


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
def cargar_usuario():
    """Deja en g.usuario la cuenta de la sesión (None si no hay o ya no existe)."""
    uid = session.get("uid")
    g.usuario = None
    if uid is not None:
        g.usuario = get_db().execute("SELECT id, usuario FROM usuarios WHERE id = ?",
                                     (uid,)).fetchone()
        if g.usuario is None:
            session.clear()


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
    return {"can_edit": g.get("usuario") is not None, "usuario": g.get("usuario"),
            "CATEGORIAS": CATEGORIAS,
            "CARROCERIAS": CARROCERIAS, "COLORES": COLORES, "TRANSMISIONES": TRANSMISIONES,
            "COMBUSTIBLES": COMBUSTIBLES, "FRENOS": FRENOS, "USOS": USOS, "HECHO_POR": HECHO_POR,
            "DOCUMENTOS": DOCUMENTOS, "REPETICIONES": REPETICIONES, "BOVEDA": archivos.BOVEDA,
            "COLOR_DEFAULT": COLOR_DEFAULT,
            "catalogo_js": catalogo_js, "logo_marca": logo_marca,
            "logo_oscuro": logo_oscuro, "nombre_auto": nombre_auto, "ficha_tecnica": ficha_tecnica,
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


def patente_info(patente):
    """Formato de la patente: ("vieja", "ALF 749") para las de 6 caracteres (1995-2016),
    ("mercosur", "AB 123 CD") para las de 7, o ("otra", tal cual) si no coincide."""
    p = re.sub(r"[^A-Z0-9]", "", (patente or "").upper())
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
    pares = [("Motor", v["motor"]), ("Combustible", COMBUSTIBLES.get(v["combustible"])),
             ("Tanque", litros(v["tanque"])), ("Código de pintura", v["codigo_pintura"]),
             ("VIN", v["vin"]), ("Aceite", aceite), ("Bujías", v["bujias"]),
             ("Refrigerante", v["refrigerante"]), ("Líquido de frenos", v["frenos"]),
             ("Neumáticos", v["neumaticos"]), ("Presión delantera", v["presion_del"]),
             ("Presión trasera", v["presion_tras"])]
    return [(k, x) for k, x in pares if x]


def nombre_auto(v):
    """Nombre a mostrar: el apodo, o marca + modelo si no tiene."""
    return (v["nombre"] or " ".join(x for x in (v["marca"], v["modelo"], v["version"]) if x)
            or "Mi vehículo")


def to_int(value):
    value = (value or "").strip().replace(".", "").replace(",", "")
    return int(value) if value.isdigit() else None


def to_float(value):
    value = (value or "").strip().replace("$", "").replace(" ", "")
    if not value:
        return None
    # Formato argentino: el punto separa miles y la coma los decimales (1.234,56).
    value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


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
    return max(v["km_inicial"] or 0, row[0] or 0)


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
    orden = {"vencido": 0, "pronto": 1, "ok": 2}
    recordatorios.sort(key=lambda x: orden[x["estado"]])
    return recordatorios


def datos_vehiculo_form():
    f = request.form
    color = f.get("color", "").strip().lower()
    if not re.fullmatch(r"#[0-9a-f]{6}", color):
        color = COLOR_DEFAULT
    carroceria = f.get("carroceria")
    marca = canon_marca(f.get("marca"))
    transmision = f.get("transmision")
    uso = f.get("uso") if f.get("calcular_uso") and f.get("uso") in USOS else None
    km_mes = to_int(f.get("km_mes"))
    if uso == "personalizado" and not (km_mes and 0 < km_mes <= KM_MES_MAX):
        flash(f"Para el plan de mantenimiento personalizado poné los km por mes (entre 1 y {KM_MES_MAX:,}"
              .replace(",", ".") + ").", "error")
        uso = None
    return {
        "version": texto("version", 60),
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
        "imagen_modo": "foto" if f.get("imagen_modo") == "foto" else "3d",
        # El plan de mantenimiento es opcional: solo con la casilla tildada.
        "uso": uso,
        "km_mes": km_mes if uso == "personalizado" else None,
    }


def to_fecha(value):
    """Fecha ISO válida (AAAA-MM-DD) o None."""
    try:
        return date.fromisoformat((value or "").strip()).isoformat()
    except ValueError:
        return None


def texto(campo, largo):
    return request.form.get(campo, "").strip()[:largo]


def datos_registro_form():
    f = request.form
    hecho_por = f.get("hecho_por") if f.get("hecho_por") in HECHO_POR else None
    return {
        "fecha": to_fecha(f.get("fecha")) or date.today().isoformat(),
        "km": to_int(f.get("km")),
        "categoria": f.get("categoria") if f.get("categoria") in CATEGORIAS else "otro",
        "titulo": texto("titulo", 120),
        "detalle": texto("detalle", 4000),
        "costo": to_float(f.get("costo")),
        "hecho_por": hecho_por,
        # Nombre del taller o de quien lo hizo; "hecho por mí" no lleva nombre.
        "taller": texto("taller", 120) if hecho_por in ("taller", "otro") else "",
        "prox_km": to_int(f.get("prox_km")),
        "prox_fecha": to_fecha(f.get("prox_fecha")),
    }


# ---------------------------------------------------------------- rutas: cuentas

# Intentos fallidos de ingreso por usuario: {usuario: [momentos]}. Frena a quien
# prueba contraseñas al azar (5 intentos cada 10 minutos).
INTENTOS = {}
MAX_INTENTOS, VENTANA = 5, 600


def bloqueado(nombre):
    ahora = time.time()
    INTENTOS[nombre] = [t for t in INTENTOS.get(nombre, []) if ahora - t < VENTANA]
    return len(INTENTOS[nombre]) >= MAX_INTENTOS


def destino_seguro():
    destino = request.args.get("next", "")
    # Solo rutas internas: "//otro-sitio.com" también empieza con "/".
    interno = destino.startswith("/") and not destino.startswith(("//", "/\\"))
    return destino if interno else url_for("index")


def iniciar_sesion(uid):
    session.clear()
    session["uid"] = uid
    session.permanent = True


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
    if len(clave) < 6:
        return "La contraseña debe tener al menos 6 caracteres."
    if len(clave) > 200:
        return "La contraseña es demasiado larga."
    if clave != clave2:
        return "Las contraseñas no coinciden."
    return None


@app.route("/registro", methods=["GET", "POST"])
def registrarse():
    if g.usuario:
        return redirect(url_for("index"))
    nombre = ""
    if request.method == "POST":
        nombre = request.form.get("usuario", "").strip()
        clave = request.form.get("clave", "")
        error = None
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,30}", nombre):
            error = "El usuario debe tener de 3 a 30 caracteres: letras, números, punto, guion o guion bajo."
        else:
            error = validar_clave(clave, request.form.get("clave2", ""))
        if error is None:
            db = get_db()
            primera = db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0
            try:
                cur = db.execute("INSERT INTO usuarios (usuario, clave, creado) VALUES (?, ?, ?)",
                                 (nombre, generate_password_hash(clave),
                                  datetime.now().isoformat(timespec="seconds")))
            except sqlite3.IntegrityError:
                error = "Ese usuario ya existe. Elegí otro."
            else:
                # Los vehículos cargados antes de que existieran las cuentas
                # pasan a la primera cuenta que se crea.
                if primera:
                    db.execute("UPDATE vehiculos SET usuario_id = ? WHERE usuario_id IS NULL",
                               (cur.lastrowid,))
                db.commit()
                iniciar_sesion(cur.lastrowid)
                nuevo_codigo(cur.lastrowid)
                flash(f"¡Bienvenido a boxes, {nombre}! Tu cuenta está lista.", "ok")
                return redirect(url_for("codigo"))
        flash(error, "error")
    return render_template("registro.html", nombre=nombre)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(url_for("index"))
    nombre = ""
    if request.method == "POST":
        nombre = request.form.get("usuario", "").strip()
        llave = nombre.lower()
        if bloqueado(llave):
            flash("Demasiados intentos. Esperá unos minutos y probá de nuevo.", "error")
            return render_template("login.html", nombre=nombre), 429
        u = get_db().execute("SELECT * FROM usuarios WHERE usuario = ?", (nombre,)).fetchone()
        if u and check_password_hash(u["clave"], request.form.get("clave", "")):
            INTENTOS.pop(llave, None)
            iniciar_sesion(u["id"])
            return redirect(destino_seguro())
        INTENTOS[llave].append(time.time())
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html", nombre=nombre)


@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    """Nueva contraseña con el código de recuperación. Usa el mismo freno de
    intentos que el ingreso, así nadie puede probar códigos al azar."""
    if g.usuario:
        return redirect(url_for("cuenta"))
    nombre = ""
    if request.method == "POST":
        nombre = request.form.get("usuario", "").strip()
        llave = nombre.lower()
        if bloqueado(llave):
            flash("Demasiados intentos. Esperá unos minutos y probá de nuevo.", "error")
            return render_template("recuperar.html", nombre=nombre), 429
        u = get_db().execute("SELECT * FROM usuarios WHERE usuario = ?", (nombre,)).fetchone()
        codigo = normalizar_codigo(request.form.get("codigo"))
        if not (u and u["codigo"] and check_password_hash(u["codigo"], codigo)):
            INTENTOS[llave].append(time.time())
            flash("Usuario o código incorrectos.", "error")
            return render_template("recuperar.html", nombre=nombre)
        error = validar_clave(request.form.get("clave", ""), request.form.get("clave2", ""))
        if error:
            flash(error, "error")
            return render_template("recuperar.html", nombre=nombre)
        get_db().execute("UPDATE usuarios SET clave = ? WHERE id = ?",
                         (generate_password_hash(request.form["clave"]), u["id"]))
        INTENTOS.pop(llave, None)
        iniciar_sesion(u["id"])
        # El código usado ya no sirve: se entrega uno nuevo.
        nuevo_codigo(u["id"])
        flash("Contraseña cambiada. Guardá tu nuevo código de recuperación.", "ok")
        return redirect(url_for("codigo"))
    return render_template("recuperar.html", nombre=nombre)


@app.route("/cuenta", methods=["GET", "POST"])
@requiere_login
def cuenta():
    if request.method == "POST":
        u = get_db().execute("SELECT * FROM usuarios WHERE id = ?", (g.usuario["id"],)).fetchone()
        if not check_password_hash(u["clave"], request.form.get("actual", "")):
            flash("La contraseña actual no es correcta.", "error")
        elif request.form.get("accion") == "codigo":
            nuevo_codigo(u["id"])
            flash("Código nuevo generado. El anterior ya no sirve.", "ok")
            return redirect(url_for("codigo"))
        else:
            error = validar_clave(request.form.get("clave", ""), request.form.get("clave2", ""))
            if error:
                flash(error, "error")
            else:
                get_db().execute("UPDATE usuarios SET clave = ? WHERE id = ?",
                                 (generate_password_hash(request.form["clave"]), u["id"]))
                get_db().commit()
                flash("Contraseña cambiada.", "ok")
                return redirect(url_for("cuenta"))
    return render_template("cuenta.html")


@app.route("/cuenta/codigo")
@requiere_login
def codigo():
    """Muestra el código de recuperación recién generado, una sola vez."""
    c = session.pop("codigo_nuevo", None)
    if c is None:
        return redirect(url_for("cuenta"))
    resp = app.make_response(render_template("codigo.html", codigo=c))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------- rutas: vehículos

CAMPOS_VEHICULO = ["imagen_modo", "km_mes", "nombre", "marca", "modelo", "version", "anio", "patente", "km_inicial", "notas",
                   "carroceria", "color", "transmision", "motor", "combustible", "tanque",
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


def lista_avisos(v, a, con_nombre=False):
    """Avisos urgentes (vencidos o por vencer) de un vehículo, para el cartel lateral."""
    nombre = nombre_auto(v)
    url = url_for("vehiculo", vid=v["id"])
    salida = []

    def agregar(clave, titulo, detalle, estado):
        salida.append({"clave": f"{v['id']}:{clave}", "titulo": titulo, "detalle": detalle,
                       "estado": estado, "url": url, "auto": nombre if con_nombre else None})

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
        agregar("rec:" + rec["registro"]["titulo"].strip().lower(), rec["registro"]["titulo"],
                " · ".join(partes), rec["estado"])
    for p in a["plan"]:
        if p["estado"] in ("vencido", "pronto"):
            detalle = "Ya toca" if p["estado"] == "vencido" else \
                f"≈ {fecha(p['fecha'])}" + (f" · {miles(p['faltan_km'])} km" if p["faltan_km"] is not None else "")
            agregar("plan:" + p["clave"], p["nombre"] + " (estimado)", detalle, p["estado"])
    for d in a["documentos"]:
        if d["estado"] not in ("vencido", "pronto") or d["dias"] is None:
            continue
        detalle = (f"Venció hace {-d['dias']} {'día' if d['dias'] == -1 else 'días'}" if d["dias"] < 0
                   else "Vence hoy" if d["dias"] == 0
                   else f"Faltan {d['dias']} {'día' if d['dias'] == 1 else 'días'}")
        agregar("doc:" + d["doc"]["tipo"], d["nombre"], detalle, d["estado"])
    salida.sort(key=lambda x: x["estado"] != "vencido")
    return salida


@app.route("/")
def index():
    if g.usuario is None:
        return render_template("bienvenida.html")
    vehiculos = get_db().execute("""
        SELECT v.*, COUNT(r.id) AS n, MAX(r.fecha) AS ultimo,
               MAX(r.km) AS max_km, COALESCE(SUM(r.costo), 0) AS gasto
        FROM vehiculos v LEFT JOIN registros r ON r.vehiculo_id = v.id
        WHERE v.usuario_id = ?
        GROUP BY v.id
        ORDER BY COALESCE(NULLIF(v.nombre, ''), v.marca || ' ' || v.modelo) COLLATE NOCASE
    """, (g.usuario["id"],)).fetchall()
    alertas, cartel = {}, []
    for v in vehiculos:
        a = avisos(v)
        alertas[v["id"]] = contar_avisos(a)
        cartel += lista_avisos(v, a, con_nombre=len(vehiculos) > 1)
    cartel.sort(key=lambda x: x["estado"] != "vencido")
    return render_template("index.html", vehiculos=vehiculos, alertas=alertas, cartel=cartel)


@app.route("/vehiculo/nuevo", methods=["GET", "POST"])
@requiere_login
def vehiculo_nuevo():
    if request.method == "POST":
        d = datos_vehiculo_form()
        d.update(usuario_id=g.usuario["id"], creado=date.today().isoformat())
        cols = list(d)
        cur = get_db().execute(
            f"INSERT INTO vehiculos ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})", d)
        get_db().commit()
        guardar_portada(cur.lastrowid)
        flash("Vehículo agregado.", "ok")
        return redirect(url_for("vehiculo", vid=cur.lastrowid))
    return render_template("vehiculo_form.html", v=None, medido=None)


@app.route("/vehiculo/<int:vid>")
@requiere_login
def vehiculo(vid):
    v = get_vehiculo(vid)
    db = get_db()
    cat = request.args.get("cat", "")
    q = request.args.get("q", "").strip()

    where, params = ["vehiculo_id = ?"], [vid]
    if cat in CATEGORIAS:
        where.append("categoria = ?")
        params.append(cat)
    if q:
        where.append("(titulo LIKE ? OR detalle LIKE ? OR taller LIKE ?)")
        params += [f"%{q}%"] * 3
    registros = db.execute(
        f"SELECT * FROM registros WHERE {' AND '.join(where)} "
        "ORDER BY fecha DESC, km DESC, id DESC", params).fetchall()

    anio = str(date.today().year)
    stats = db.execute("""
        SELECT COUNT(*) AS n, COALESCE(SUM(costo), 0) AS total,
               COALESCE(SUM(CASE WHEN substr(fecha, 1, 4) = ? THEN costo END), 0) AS anio
        FROM registros WHERE vehiculo_id = ?""", (anio, vid)).fetchone()
    todos = registros_de(vid)
    a = avisos(v, todos)
    boveda = db.execute("SELECT * FROM archivos WHERE vehiculo_id = ? AND registro_id IS NULL "
                        "AND COALESCE(categoria, '') <> 'portada' ORDER BY categoria, id", (vid,)).fetchall()
    return render_template(
        "vehiculo.html", v=v, registros=registros, stats=stats, km_real=km_actual(v),
        km_hoy=a["km_hoy"], recordatorios=a["recordatorios"], plan=a["plan"],
        documentos=a["documentos"], boveda=boveda, adjuntos=adjuntos_por_registro(vid),
        cat=cat, q=q, anio=anio, espacio=espacio_usado(), cartel=lista_avisos(v, a))


@app.route("/vehiculo/<int:vid>/editar", methods=["GET", "POST"])
@requiere_login
def vehiculo_editar(vid):
    v = get_vehiculo(vid)
    if request.method == "POST":
        d = datos_vehiculo_form()
        d["id"] = vid
        get_db().execute(
            f"UPDATE vehiculos SET {', '.join(f'{c} = :{c}' for c in CAMPOS_VEHICULO)} WHERE id = :id", d)
        get_db().commit()
        guardar_portada(vid)
        flash("Datos del vehículo actualizados.", "ok")
        return redirect(url_for("vehiculo", vid=vid))
    return render_template("vehiculo_form.html", v=v, medido=promedio_medido(registros_de(vid)))


@app.route("/vehiculo/<int:vid>/eliminar", methods=["POST"])
@requiere_login
def vehiculo_eliminar(vid):
    get_vehiculo(vid)
    db = get_db()
    nombres = [r[0] for r in db.execute("SELECT archivo FROM archivos WHERE vehiculo_id = ?", (vid,))]
    db.execute("DELETE FROM vehiculos WHERE id = ?", (vid,))
    db.commit()
    archivos.borrar(nombres)
    flash("Vehículo eliminado.", "ok")
    return redirect(url_for("index"))


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


@app.route("/vehiculo/<int:vid>/exportar")
@requiere_login
def vehiculo_exportar(vid):
    v = get_vehiculo(vid)
    rows = get_db().execute(
        "SELECT * FROM registros WHERE vehiculo_id = ? ORDER BY fecha, km, id", (vid,)
    ).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Fecha", "Km", "Categoría", "Trabajo", "Detalle", "Costo",
                "Hecho por", "Próximo km", "Próxima fecha"])
    for r in rows:
        w.writerow([celda_csv(x) for x in (
            r["fecha"], r["km"] or "", CATEGORIAS.get(r["categoria"], r["categoria"]),
            r["titulo"], r["detalle"] or "", r["costo"] if r["costo"] is not None else "",
            quien(r), r["prox_km"] or "", r["prox_fecha"] or "")])
    nombre = "".join(c if c.isalnum() else "_" for c in nombre_auto(v))
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=bitacora_{nombre}.csv"})


# ---------------------------------------------------------------- rutas: documentación

@app.route("/vehiculo/<int:vid>/documentos", methods=["GET", "POST"])
@requiere_login
def documentos(vid):
    v = get_vehiculo(vid)
    db = get_db()
    if request.method == "POST":
        for tipo in DOCUMENTOS:
            vence = to_fecha(request.form.get(f"vence_{tipo}"))
            detalle = texto(f"detalle_{tipo}", 120)
            cada = to_int(request.form.get(f"cada_{tipo}"))
            cada = cada if cada in REPETICIONES else None
            if not vence and not detalle:
                db.execute("DELETE FROM documentos WHERE vehiculo_id = ? AND tipo = ?", (vid, tipo))
                continue
            db.execute("INSERT INTO documentos (vehiculo_id, tipo, vence, cada_meses, detalle) "
                       "VALUES (?, ?, ?, ?, ?) ON CONFLICT (vehiculo_id, tipo) DO UPDATE SET "
                       "vence = excluded.vence, cada_meses = excluded.cada_meses, "
                       "detalle = excluded.detalle", (vid, tipo, vence, cada, detalle))
        db.commit()
        flash("Vencimientos guardados.", "ok")
        return redirect(url_for("vehiculo", vid=vid) + "#documentacion")
    docs = {d["tipo"]: d for d in documentos_de(vid)}
    return render_template("documentos.html", v=v, docs=docs, sugerida=REPETICION_SUGERIDA)


@app.route("/documento/<int:did>/renovar", methods=["POST"])
@requiere_login
def documento_renovar(did):
    """"Ya lo pagué / renové": corre el vencimiento según cada cuánto se repite."""
    d = get_db().execute("SELECT * FROM documentos WHERE id = ?", (did,)).fetchone()
    if d is None:
        abort(404)
    get_vehiculo(d["vehiculo_id"])
    vence = date.fromisoformat(d["vence"]) if d["vence"] else None
    if vence and d["cada_meses"]:
        nueva = sumar_meses(vence, d["cada_meses"])
        get_db().execute("UPDATE documentos SET vence = ? WHERE id = ?", (nueva.isoformat(), did))
        get_db().commit()
        flash(f"{DOCUMENTOS.get(d['tipo'], 'Vencimiento')}: el próximo es el {fecha(nueva.isoformat())}.", "ok")
    return redirect(url_for("vehiculo", vid=d["vehiculo_id"]) + "#documentacion")


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


@app.route("/vehiculo/<int:vid>/boveda", methods=["POST"])
@requiere_login
def boveda_subir(vid):
    get_vehiculo(vid)
    categoria = request.form.get("categoria")
    n = subir_archivos(vid, categoria=categoria if categoria in archivos.BOVEDA else "otro")
    if n:
        flash("Documento guardado en la bóveda." if n == 1 else f"{n} documentos guardados en la bóveda.", "ok")
    elif not request.files.getlist("archivos"):
        flash("Elegí un archivo para subir.", "error")
    return redirect(url_for("vehiculo", vid=vid) + "#boveda")


@app.route("/archivo/<int:aid>")
@requiere_login
def archivo(aid):
    return enviar_archivo(get_archivo(aid))


@app.route("/archivo/<int:aid>/eliminar", methods=["POST"])
@requiere_login
def archivo_eliminar(aid):
    a = get_archivo(aid)
    get_db().execute("DELETE FROM archivos WHERE id = ?", (aid,))
    get_db().commit()
    archivos.borrar([a["archivo"]])
    flash("Archivo eliminado.", "ok")
    destino = url_for("registro_editar", rid=a["registro_id"]) if a["registro_id"] else \
        url_for("vehiculo", vid=a["vehiculo_id"]) + "#boveda"
    return redirect(destino)


@app.route("/sw.js")
def service_worker():
    """El service worker guarda una copia de lo que se ve, para abrir la bóveda
    sin conexión. Se sirve desde la raíz para que cubra todo el sitio."""
    resp = send_file(os.path.join(BASE_DIR, "static", "sw.js"), mimetype="text/javascript", max_age=0)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


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


@app.route("/vehiculo/<int:vid>/libro")
@requiere_login
def libro(vid):
    v = get_vehiculo(vid)
    return render_template("libro.html", compartido=False,
                           url_archivo=lambda aid: url_for("archivo", aid=aid), **datos_libro(v))


@app.route("/vehiculo/<int:vid>/compartir", methods=["GET", "POST"])
@requiere_login
def compartir(vid):
    v = get_vehiculo(vid)
    if request.method == "POST":
        accion = request.form.get("accion")
        db = get_db()
        if accion in ("activar", "regenerar"):
            db.execute("UPDATE vehiculos SET share_token = ? WHERE id = ?", (secrets.token_urlsafe(12), vid))
            flash("Link nuevo creado. El anterior ya no funciona." if accion == "regenerar"
                  else "Link para compartir creado.", "ok")
        elif accion == "desactivar":
            db.execute("UPDATE vehiculos SET share_token = NULL WHERE id = ?", (vid,))
            flash("Dejaste de compartir la bitácora. El link ya no funciona.", "ok")
        elif accion == "opciones":
            db.execute("UPDATE vehiculos SET share_costos = ?, share_adjuntos = ? WHERE id = ?",
                       (1 if request.form.get("costos") else 0, 1 if request.form.get("adjuntos") else 0, vid))
            flash("Opciones guardadas.", "ok")
        db.commit()
        return redirect(url_for("compartir", vid=vid))
    link = url_for("compartido", token=v["share_token"], _external=True) if v["share_token"] else None
    return render_template("compartir.html", v=v, link=link)


def vehiculo_compartido(token):
    v = get_db().execute("SELECT * FROM vehiculos WHERE share_token = ?", (token,)).fetchone()
    if v is None:
        abort(404)
    return v


@app.route("/c/<token>")
def compartido(token):
    """Bitácora compartida: solo lectura, sin cuenta. No muestra documentación,
    bóveda ni vencimientos, que son datos personales del dueño."""
    v = vehiculo_compartido(token)
    resp = app.make_response(render_template(
        "libro.html", compartido=True,
        url_archivo=lambda aid: url_for("archivo_compartido", token=token, aid=aid),
        **datos_libro(v, bool(v["share_costos"]), bool(v["share_adjuntos"]))))
    resp.headers["X-Robots-Tag"] = "noindex"
    return resp


@app.route("/c/<token>/archivo/<int:aid>")
def archivo_compartido(token, aid):
    v = vehiculo_compartido(token)
    a = get_db().execute("SELECT * FROM archivos WHERE id = ? AND vehiculo_id = ? "
                         "AND (registro_id IS NOT NULL OR categoria = 'portada')", (aid, v["id"])).fetchone()
    if a is None or (a["categoria"] != "portada" and not v["share_adjuntos"]):
        abort(404)
    return enviar_archivo(a)


# ---------------------------------------------------------------- rutas: registros

def guardar_registro(v, rid=None):
    """Alta o edición de un registro con sus fotos y facturas."""
    d = datos_registro_form()
    if not d["titulo"]:
        flash("Indicá qué trabajo se hizo.", "error")
        return render_template("registro_form.html", v=v, r={**d, "id": rid},
                               adjuntos=adjuntos_por_registro(v["id"]).get(rid, []))
    db = get_db()
    if rid is None:
        d["vehiculo_id"] = v["id"]
        rid = db.execute(
            "INSERT INTO registros (vehiculo_id, fecha, km, categoria, titulo, detalle, costo, "
            "taller, hecho_por, prox_km, prox_fecha) VALUES (:vehiculo_id, :fecha, :km, :categoria, "
            ":titulo, :detalle, :costo, :taller, :hecho_por, :prox_km, :prox_fecha)", d).lastrowid
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


@app.route("/vehiculo/<int:vid>/registro/nuevo", methods=["GET", "POST"])
@requiere_login
def registro_nuevo(vid):
    v = get_vehiculo(vid)
    if request.method == "POST":
        return guardar_registro(v)
    titulo = request.args.get("titulo", "")[:120]
    nuevo = {"fecha": date.today().isoformat(), "km": km_actual(v) or None,
             "categoria": request.args.get("cat", "control"), "titulo": titulo}
    return render_template("registro_form.html", v=v, r=nuevo, adjuntos=[])


@app.route("/registro/<int:rid>/editar", methods=["GET", "POST"])
@requiere_login
def registro_editar(rid):
    r = get_db().execute("SELECT * FROM registros WHERE id = ?", (rid,)).fetchone()
    if r is None:
        abort(404)
    v = get_vehiculo(r["vehiculo_id"])
    if request.method == "POST":
        return guardar_registro(v, rid)
    return render_template("registro_form.html", v=v, r=r,
                           adjuntos=adjuntos_por_registro(v["id"]).get(rid, []))


@app.route("/registro/<int:rid>/eliminar", methods=["POST"])
@requiere_login
def registro_eliminar(rid):
    r = get_db().execute("SELECT vehiculo_id FROM registros WHERE id = ?", (rid,)).fetchone()
    if r is None:
        abort(404)
    get_vehiculo(r["vehiculo_id"])
    db = get_db()
    nombres = [x[0] for x in db.execute("SELECT archivo FROM archivos WHERE registro_id = ?", (rid,))]
    db.execute("DELETE FROM registros WHERE id = ?", (rid,))
    db.commit()
    archivos.borrar(nombres)
    flash("Registro eliminado.", "ok")
    return redirect(url_for("vehiculo", vid=r["vehiculo_id"]))


@app.errorhandler(404)
def no_encontrado(e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def muy_grande(e):
    return render_template("404.html", codigo="Uy", titulo="Archivos demasiado pesados",
                           mensaje="Lo que intentaste subir pasa los 45 MB en total. "
                                   "Probá con menos archivos o más livianos."), 413


if __name__ == "__main__":
    app.run(debug=True)
