"""Registros de mantenimiento: alta, edición y baja."""
from nucleo import *  # noqa: F401,F403


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
