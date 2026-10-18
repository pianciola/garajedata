"""Importar la copia .zip que se descarga en «Mis datos» (por ejemplo, para pasar todo a una cuenta nueva
si se perdieron la contraseña y el código de recuperación)."""
import zipfile
import zlib

from nucleo import *  # noqa: F401,F403

MAX_JSON = 8 * 1024 * 1024            # garajedata.json descomprimido
MAX_DESCOMPRIMIDO = 150 * 1024 * 1024  # todo el zip descomprimido (frena las «bombas» de zip)
MAX_VEHICULOS = 50
MAX_REGISTROS = 5000

# Columnas que se aceptan de cada tabla, con su tipo. Nada de ids, dueños, tokens ni fechas internas.
COLS_VEHICULO = {c: "txt" for c in CAMPOS_VEHICULO}
COLS_VEHICULO.update({c: "int" for c in ("anio", "cilindrada", "km_inicial", "km_mes", "foto_x", "foto_y", "foto_zoom", "km_manual")})
COLS_VEHICULO.update({"tanque": "num", "aceite_litros": "num", "km_manual_fecha": "fecha"})
COLS_REGISTRO = {"fecha": "fecha", "km": "int", "categoria": "txt", "titulo": "txt", "detalle": "txt", "costo": "num",
                 "taller": "txt", "hecho_por": "txt", "prox_km": "int", "prox_fecha": "fecha"}
COLS_DOCUMENTO = {"tipo": "txt", "vence": "fecha", "cada_meses": "int", "detalle": "txt"}


class ArchivoDelZip:
    """Imita al archivo de un formulario para reutilizar las mismas validaciones que una subida normal."""

    def __init__(self, datos, nombre):
        self._datos, self.filename = datos, nombre

    def read(self, n=-1):
        return self._datos if n < 0 else self._datos[:n]


def valor(v, tipo):
    """Normaliza un valor del JSON al tipo esperado; lo que no encaja queda en None."""
    if v is None:
        return None
    if tipo == "int":
        return v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v < 10 ** 12 else None
    if tipo == "num":
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and abs(v) < 1e12 else None
    if tipo == "fecha":
        return to_fecha(v) if isinstance(v, str) else None
    return str(v)[:4000] if isinstance(v, (str, int, float)) else None


def limpiar(fila, columnas):
    return {c: valor(fila.get(c), t) for c, t in columnas.items() if c in fila}


def validar_estructura(datos):
    """Rechaza copias dañadas antes de escribir datos o archivos."""
    error = "La estructura de la copia no es válida. Volvé a descargarla desde Mis datos."
    if not isinstance(datos, dict) or not isinstance(datos.get("vehiculos"), list):
        raise ValueError(error)
    vehiculos = datos["vehiculos"]
    if len(vehiculos) > MAX_VEHICULOS:
        raise ValueError("La copia tiene demasiados vehículos para importarla de una vez.")
    registros = 0
    for v in vehiculos:
        if not isinstance(v, dict):
            raise ValueError(error)
        for campo in ("registros", "documentos", "pendientes", "archivos"):
            items = v.get(campo)
            if items is None:
                continue
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                raise ValueError(error)
            if campo == "registros":
                registros += len(items)
            for item in items:
                for nombre in ("id", "registro_id"):
                    ident = item.get(nombre)
                    if ident is not None and (type(ident) is not int or ident < 1):
                        raise ValueError(error)
        ids = [r["id"] for r in (v.get("registros") or []) if r.get("id") is not None]
        if len(ids) != len(set(ids)):
            raise ValueError(error)
    if registros > MAX_REGISTROS:
        raise ValueError("La copia tiene demasiados registros para importarla de una vez.")
    return vehiculos


def importar_zip(contenido):
    """Agrega a la cuenta actual los vehículos de un zip exportado. Devuelve (vehículos, registros, archivos, avisos)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(contenido))
    except zipfile.BadZipFile:
        raise ValueError("El archivo no es un .zip válido.")
    with z:
        if sum(i.file_size for i in z.infolist()) > MAX_DESCOMPRIMIDO:
            raise ValueError("El .zip es demasiado grande.")
        try:
            info = z.getinfo("garajedata.json")
        except KeyError:
            raise ValueError("Ese .zip no es una copia de GarajeData (le falta garajedata.json).")
        if info.file_size > MAX_JSON:
            raise ValueError("El archivo de datos es demasiado grande.")
        try:
            datos = json.loads(z.read(info).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error):
            raise ValueError("No se pudo leer garajedata.json: el archivo está dañado o fue modificado.")
        vehiculos = validar_estructura(datos)

        db = get_db()
        uid = g.usuario["id"]
        usados = espacio_usado()
        avisos, nuevos_archivos = [], []
        n_veh = n_reg = n_arch = 0
        fuera_de_rango = 0
        ultimo = db.execute("SELECT MAX(orden) FROM vehiculos WHERE usuario_id = ?", (uid,)).fetchone()[0] or 0
        try:
            for v in vehiculos:
                if not isinstance(v, dict):
                    continue
                fila = limpiar(v, COLS_VEHICULO)
                fila["nombre"] = fila.get("nombre") or ""
                # Un kilometraje que no puede ser real no se importa (avisado al final).
                for campo in ("km_inicial", "km_manual"):
                    if fila.get(campo) is not None and fila[campo] > KM_MAX:
                        fila[campo] = None
                        fuera_de_rango += 1
                if fila.get("imagen_modo") not in ("3d", "foto"):
                    fila["imagen_modo"] = "3d"
                ultimo += 1
                fila.update(usuario_id=uid, creado=date.today().isoformat(), orden=ultimo)
                cols = list(fila)
                vid = db.execute(f"INSERT INTO vehiculos ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                                 [fila[c] for c in cols]).lastrowid
                n_veh += 1
                ids_reg = {}
                for r in v.get("registros") or []:
                    if not isinstance(r, dict):
                        continue
                    fr = limpiar(r, COLS_REGISTRO)
                    if not fr.get("titulo"):
                        continue
                    fr["titulo"] = fr["titulo"][:120]
                    fr["fecha"] = fr.get("fecha") or date.today().isoformat()
                    fr["categoria"] = categoria_valida(fr.get("categoria"))
                    if fr.get("hecho_por") not in HECHO_POR:
                        fr["hecho_por"] = None
                    for campo in ("km", "prox_km"):
                        if fr.get(campo) is not None and fr[campo] > KM_MAX:
                            fr[campo] = None
                            fuera_de_rango += 1
                    fr["vehiculo_id"] = vid
                    cols = list(fr)
                    ids_reg[r.get("id")] = db.execute(
                        f"INSERT INTO registros ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                        [fr[c] for c in cols]).lastrowid
                    n_reg += 1
                for d in v.get("documentos") or []:
                    if not isinstance(d, dict):
                        continue
                    fd = limpiar(d, COLS_DOCUMENTO)
                    if fd.get("tipo") not in DOCUMENTOS:
                        continue
                    if fd.get("cada_meses") not in REPETICIONES:
                        fd["cada_meses"] = None
                    db.execute("INSERT OR REPLACE INTO documentos (vehiculo_id, tipo, vence, cada_meses, detalle) VALUES (?, ?, ?, ?, ?)",
                               (vid, fd["tipo"], fd.get("vence"), fd.get("cada_meses"), (fd.get("detalle") or "")[:120]))
                for p in (v.get("pendientes") or [])[:200]:
                    if not isinstance(p, dict) or not isinstance(p.get("titulo"), str) or not p["titulo"].strip():
                        continue
                    km_p = valor(p.get("km"), "int")
                    fecha_p = valor(p.get("fecha"), "fecha")
                    if not (km_p or fecha_p):
                        continue
                    db.execute("INSERT INTO pendientes (vehiculo_id, titulo, categoria, fecha, km, detalle, creado) "
                               "VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (vid, p["titulo"].strip()[:120], categoria_valida(valor(p.get("categoria"), "txt")), fecha_p, km_p,
                                (valor(p.get("detalle"), "txt") or None), datetime.now().isoformat(timespec="seconds")))
                foto_vieja = v.get("foto_id")
                for a in v.get("archivos") or []:
                    if not isinstance(a, dict) or not isinstance(a.get("en_el_zip"), str):
                        continue
                    registro = ids_reg.get(a.get("registro_id")) if a.get("registro_id") is not None else None
                    if a.get("registro_id") is not None and registro is None:
                        continue  # No guardar archivos huérfanos de registros descartados.
                    try:
                        crudo = z.read(a["en_el_zip"])
                    except KeyError:
                        continue
                    try:
                        en_disco, mime, peso, nombre = archivos.guardar(
                            ArchivoDelZip(crudo, str(a.get("nombre") or "archivo")), usados)
                    except ValueError as e:
                        avisos.append(str(e))
                        continue
                    nuevos_archivos.append(en_disco)
                    usados += peso
                    categoria = valor(a.get("categoria"), "txt")
                    if categoria not in archivos.BOVEDA and categoria != "portada":
                        categoria = None
                    aid = db.execute("INSERT INTO archivos (vehiculo_id, registro_id, categoria, nombre, archivo, mime, bytes, creado) "
                                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                     (vid, registro, categoria, nombre, en_disco, mime, peso,
                                      datetime.now().isoformat(timespec="seconds"))).lastrowid
                    n_arch += 1
                    if foto_vieja is not None and a.get("id") == foto_vieja:
                        db.execute("UPDATE vehiculos SET foto_id = ? WHERE id = ?", (aid, vid))
            db.commit()
        except Exception:
            db.rollback()
            archivos.borrar(nuevos_archivos)
            raise
    if fuera_de_rango:
        avisos.append(f"{fuera_de_rango} kilometraje(s) que no pueden ser reales quedaron afuera.")
    return n_veh, n_reg, n_arch, avisos


@app.post("/cuenta/importar")
@requiere_login
def importar():
    archivo = request.files.get("copia")
    if not archivo or not archivo.filename:
        flash("Elegí el archivo .zip que descargaste de GarajeData.", "error")
        return redirect(url_for("cuenta") + "#datos")
    try:
        n_veh, n_reg, n_arch, avisos = importar_zip(archivo.read(45 * 1024 * 1024 + 1))
    except (ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error) as e:
        flash(str(e) if isinstance(e, ValueError) else "La copia está dañada o no se puede descomprimir.", "error")
        return redirect(url_for("cuenta") + "#datos")
    if not n_veh:
        flash("La copia no tenía vehículos para importar.", "error")
        return redirect(url_for("cuenta") + "#datos")
    flash(f"Importado: {n_veh} {'vehículo' if n_veh == 1 else 'vehículos'}, {n_reg} registros y {n_arch} archivos."
          + (f" Algunos archivos no entraron: {avisos[0]}" if avisos else ""), "ok")
    return redirect(url_for("index"))
