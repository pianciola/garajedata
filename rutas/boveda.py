"""Bóveda digital y archivos adjuntos; service worker."""
from nucleo import *  # noqa: F401,F403


@app.route("/vehiculo/<int:vid>/boveda", methods=["POST"])
@requiere_login
def boveda_subir(vid):
    get_vehiculo(vid)
    categoria = request.form.get("categoria")
    categoria = categoria if categoria in archivos.BOVEDA else "otro"
    n = subir_archivos(vid, categoria=categoria)
    if n:
        flash("Documento guardado en la bóveda." if n == 1 else f"{n} documentos guardados en la bóveda.", "ok")
    elif not request.files.getlist("archivos"):
        flash("Elegí un archivo para subir.", "error")
    return redirect(url_for("vehiculo", vid=vid, boveda=categoria) + "#boveda")


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
        url_for("vehiculo", vid=a["vehiculo_id"], boveda=a["categoria"]) + "#boveda"
    return redirect(destino)


@app.route("/sw.js")
def service_worker():
    """El service worker guarda una copia de lo que se ve, para abrir la bóveda
    sin conexión. Se sirve desde la raíz para que cubra todo el sitio."""
    resp = send_file(os.path.join(BASE_DIR, "static", "sw.js"), mimetype="text/javascript", max_age=0)
    resp.headers["Cache-Control"] = "no-cache"
    return resp
