"""Tus datos: descargarlos todos, el calendario de avisos."""
import zipfile
from tempfile import SpooledTemporaryFile

from nucleo import *  # noqa: F401,F403


def filas(sql, params):
    return [dict(r) for r in get_db().execute(sql, params).fetchall()]


def csv_registros(regs):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Fecha", "Km", "Categoría", "Trabajo", "Detalle", "Costo",
                "Hecho por", "Próximo km", "Próxima fecha"])
    for r in regs:
        w.writerow([celda_csv(x) for x in (
            r["fecha"], r["km"] or "", CATEGORIAS.get(r["categoria"], r["categoria"]),
            r["titulo"], r["detalle"] or "", r["costo"] if r["costo"] is not None else "",
            quien(r), r["prox_km"] or "", r["prox_fecha"] or "")])
    return "﻿" + buf.getvalue()


@app.route("/cuenta/exportar")
@requiere_login
def exportar_todo():
    """Un .zip con todo lo de la cuenta: datos en JSON, registros en CSV (para Excel)
    y los archivos de la bóveda y de los registros."""
    uid = g.usuario["id"]
    vehiculos = filas("SELECT * FROM vehiculos WHERE usuario_id = ? ORDER BY orden, id", (uid,))
    salida = {"cuenta": g.usuario["usuario"], "exportado": datetime.now().isoformat(timespec="seconds"),
              "vehiculos": []}
    buf = SpooledTemporaryFile(max_size=20 * 1024 * 1024)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for v in vehiculos:
            for privado in ("share_token", "transfer_codigo", "transfer_vence", "usuario_id"):
                v.pop(privado, None)
            vid = v["id"]
            carpeta = "".join(c if c.isalnum() else "_" for c in nombre_auto(v)) + f"_{vid}"
            regs = filas("SELECT * FROM registros WHERE vehiculo_id = ? ORDER BY fecha, km, id", (vid,))
            docs = filas("SELECT * FROM documentos WHERE vehiculo_id = ?", (vid,))
            arch = filas("SELECT id, registro_id, categoria, nombre, archivo, mime, bytes, creado "
                         "FROM archivos WHERE vehiculo_id = ?", (vid,))
            for a in arch:
                nombre = "".join(c if c.isalnum() or c in "._-" else "_" for c in (a["nombre"] or "archivo"))
                destino = f"{carpeta}/archivos/{a['id']}_{nombre}"
                try:
                    z.write(archivos.ruta(a["archivo"]), destino)
                    a["en_el_zip"] = destino
                except OSError:
                    a["en_el_zip"] = None
                a.pop("archivo")
            salida["vehiculos"].append({**v, "registros": regs, "documentos": docs, "archivos": arch})
            z.writestr(f"{carpeta}/registros.csv", csv_registros(regs))
        z.writestr("garajedata.json", json.dumps(salida, ensure_ascii=False, indent=2, default=str))
        z.writestr("LEEME.txt", "Copia de tus datos de GarajeData.\n\n"
                   "garajedata.json: todos los datos (vehículos, registros, documentos y archivos).\n"
                   "Cada carpeta de vehículo tiene registros.csv (se abre con Excel) y sus archivos.\n")
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name=f"garajedata_{g.usuario['usuario']}_{date.today().isoformat()}.zip")


# ---------------------------------------------------------------- calendario (.ics)

def ics_texto(t):
    return (str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\n", "\\n"))


def eventos_de(uid):
    """(id del evento, día, título, detalle) de lo que viene en cada vehículo."""
    hoy = date.today()
    salida = []
    for v in get_db().execute("SELECT * FROM vehiculos WHERE usuario_id = ?", (uid,)).fetchall():
        a = avisos(v)
        auto = nombre_auto(v)
        kpm = km_por_mes(v) or 1250
        for r in a["recordatorios"]:
            reg = r["registro"]
            dias = [d for d in (r["faltan_dias"],
                                round(r["faltan_km"] / kpm * 30.44) if r["faltan_km"] is not None else None)
                    if d is not None]
            if not dias:
                continue
            detalle = f"Próximo a los {miles(reg['prox_km'])} km" if reg["prox_km"] else ""
            salida.append((f"rec-{reg['id']}", hoy + timedelta(days=max(0, min(dias))),
                           f"{reg['titulo']} · {auto}", detalle))
        for p in a["plan"]:
            if p.get("fecha"):
                salida.append((f"plan-{v['id']}-{p['clave']}", max(hoy, date.fromisoformat(p["fecha"])),
                               f"{p['nombre']} (estimado) · {auto}",
                               f"Cada {miles(p['cada_km'])} km o {p['cada_meses']} meses"))
        for d in a["documentos"]:
            if d["dias"] is not None:
                salida.append((f"doc-{d['doc']['id']}", date.fromisoformat(d["doc"]["vence"]),
                               f"Vence: {d['nombre']} · {auto}", d["doc"]["detalle"] or ""))
    return salida


@app.route("/cal/<token>.ics")
def calendario(token):
    u = get_db().execute("SELECT id FROM usuarios WHERE cal_token = ?", (token,)).fetchone() \
        if len(token) >= 20 else None
    if u is None:
        abort(404)
    sello = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//GarajeData//Avisos//ES", "CALSCALE:GREGORIAN",
              "X-WR-CALNAME:GarajeData", "X-PUBLISHED-TTL:PT12H", "REFRESH-INTERVAL;VALUE=DURATION:PT12H"]
    for euid, dia, titulo, detalle in eventos_de(u["id"]):
        lineas += ["BEGIN:VEVENT", f"UID:{euid}@garajedata", f"DTSTAMP:{sello}",
                   f"DTSTART;VALUE=DATE:{dia.strftime('%Y%m%d')}",
                   f"DTEND;VALUE=DATE:{(dia + timedelta(days=1)).strftime('%Y%m%d')}",
                   f"SUMMARY:{ics_texto(titulo)}", f"DESCRIPTION:{ics_texto(detalle)}",
                   # Aviso el día anterior a las 9 de la mañana.
                   "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{ics_texto(titulo)}",
                   "TRIGGER:-PT15H", "END:VALARM", "END:VEVENT"]
    lineas.append("END:VCALENDAR")
    return Response("\r\n".join(lineas) + "\r\n", mimetype="text/calendar",
                    headers={"Content-Disposition": "inline; filename=garajedata.ics",
                             "Cache-Control": "no-store"})


@app.post("/cuenta/calendario")
@requiere_login
def calendario_link():
    nuevo = secrets.token_urlsafe(24) if request.form.get("accion") != "quitar" else None
    get_db().execute("UPDATE usuarios SET cal_token = ? WHERE id = ?", (nuevo, g.usuario["id"]))
    get_db().commit()
    flash("Link del calendario creado. Agregalo a tu app de calendario." if nuevo
          else "Link del calendario desactivado.", "ok")
    return redirect(url_for("cuenta") + "#calendario")
