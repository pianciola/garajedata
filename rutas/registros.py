"""Registros de mantenimiento: alta, edición y baja."""
from nucleo import *  # noqa: F401,F403

@app.get("/cargar")
@requiere_login
def carga_rapida():
    """Compatibilidad con enlaces anteriores al formulario único."""
    return redirect(url_for("elegir_registro", vid=request.args.get("vid")))


@app.get("/registro/nuevo")
@requiere_login
def elegir_registro():
    elegido = to_int(request.args.get("vid"))
    if elegido is not None:
        v = get_vehiculo(elegido)
        return redirect(url_for("registro_nuevo", vid=v["id"]))
    vehiculos = get_db().execute("SELECT * FROM vehiculos WHERE usuario_id = ? ORDER BY orden, id",
                                 (g.usuario["id"],)).fetchall()
    if not vehiculos:
        return redirect(url_for("vehiculo_nuevo"))
    if len(vehiculos) == 1:
        return redirect(url_for("registro_nuevo", vid=vehiculos[0]["id"]))
    return render_template("registro_vehiculo.html", vehiculos=vehiculos)


@app.route("/vehiculo/<int:vid>/registro/nuevo", methods=["GET", "POST"])
@requiere_login
def registro_nuevo(vid):
    v = get_vehiculo(vid)
    if request.method == "POST":
        return guardar_registro(v)
    titulo = request.args.get("titulo", "")[:120]
    nuevo = {"fecha": date.today().isoformat(), "km": km_actual(v) or None,
             "categoria": categoria_valida(request.args.get("cat", "control")), "titulo": titulo}
    modo = "pendiente" if request.args.get("modo") == "pendiente" else "hecho"
    return render_template("registro_form.html", v=v, r=nuevo, adjuntos=[], modo=modo)


@app.post("/pendiente/<int:pid>/hecho")
@requiere_login
def pendiente_hecho(pid):
    """«Ya lo hice»: abre el registro con lo del pendiente; al guardarlo, el pendiente se cierra."""
    p = get_pendiente(pid)
    v = get_vehiculo(p["vehiculo_id"])
    nuevo = {"fecha": date.today().isoformat(), "km": km_actual(v) or None, "titulo": p["titulo"],
             "categoria": categoria_valida(p["categoria"]), "detalle": p["detalle"], "pendiente": p["id"]}
    return render_template("registro_form.html", v=v, r=nuevo, adjuntos=[], modo="hecho")


@app.post("/pendiente/<int:pid>/borrar")
@requiere_login
def pendiente_borrar(pid):
    p = get_pendiente(pid)
    get_db().execute("DELETE FROM pendientes WHERE id = ?", (p["id"],))
    get_db().commit()
    flash("Pendiente eliminado.", "ok")
    return redirect(url_for("vehiculo", vid=p["vehiculo_id"], _anchor="controles"))


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
