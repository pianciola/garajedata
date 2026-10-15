"""Libro de servicio (PDF) y bitácoras compartidas en modo lectura."""
from nucleo import *  # noqa: F401,F403


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
    link = url_absoluta("compartido", token=v["share_token"]) if v["share_token"] else None
    return render_template("compartir.html", v=v, link=link)


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
