"""Registros de mantenimiento: alta, edición y baja."""
from nucleo import *  # noqa: F401,F403

RAPIDOS = {
    "service": ("Service", "control"),
    "combustible": ("Carga de combustible", "combustible"),
    "aceite": ("Cambio de aceite y filtro", "fluidos"),
    "neumaticos": ("Neumáticos", "piezas"),
    "reparacion": ("Reparación", "reparacion"),
    "accesorios": ("Accesorios", "accesorios"),
    "lavado": ("Lavado y estética", "lavado"),
    "seguro": ("Seguro", "seguro"),
    "patente": ("Patente", "patente"),
    "vtv": ("VTV / RTO", "vtv"),
    "estacionamiento": ("Estacionamiento y cochera", "estacionamiento"),
    "peajes": ("Peajes", "peajes"),
    "multas": ("Multas", "multas"),
    "tramites": ("Trámites y transferencias", "tramites"),
    "otro": ("Otro gasto", "otro"),
}

GRUPOS_RAPIDOS = (
    ("Mantenimiento y cuidado", ("service", "combustible", "neumaticos", "reparacion", "accesorios", "lavado")),
    ("Gastos y papeles", ("seguro", "patente", "vtv", "estacionamiento", "peajes", "multas", "tramites")),
)


@app.route("/cargar", methods=["GET", "POST"])
@requiere_login
def carga_rapida():
    vehiculos = get_db().execute("SELECT * FROM vehiculos WHERE usuario_id = ? ORDER BY orden, id",
                                 (g.usuario["id"],)).fetchall()
    elegido = to_int(request.form.get("vid") if request.method == "POST" else request.args.get("vid"))
    v = get_vehiculo(elegido) if elegido is not None else None
    if not vehiculos:
        flash("Agregá un vehículo para cargar su primer gasto o service.", "ok")
        return redirect(url_for("vehiculo_nuevo"))
    if request.method == "POST":
        if v is None:
            flash("Elegí el vehículo.", "error")
        elif request.form.get("tipo") not in RAPIDOS:
            flash("Elegí qué querés cargar.", "error")
        elif request.form.get("costo", "").strip() and to_float(request.form.get("costo")) is None:
            flash("Revisá el importe del gasto.", "error")
        else:
            titulo, categoria = RAPIDOS[request.form["tipo"]]
            if request.form["tipo"] == "service" and request.form.get("servicio") == "aceite":
                titulo, categoria = RAPIDOS["aceite"]
            d = datos_registro_form()
            d.update(vehiculo_id=v["id"], titulo=d["titulo"] or titulo, categoria=categoria)
            get_db().execute("""INSERT INTO registros
                (vehiculo_id,fecha,km,categoria,titulo,costo,detalle,taller,hecho_por,prox_km,prox_fecha)
                VALUES (:vehiculo_id,:fecha,:km,:categoria,:titulo,:costo,:detalle,:taller,:hecho_por,:prox_km,:prox_fecha)""", d)
            get_db().commit()
            flash("Listo, guardado en la bitácora.", "ok")
            return redirect(url_for("vehiculo", vid=v["id"]))
    return render_template("carga_rapida.html", vehiculos=vehiculos, v=v, rapidos=RAPIDOS, grupos_rapidos=GRUPOS_RAPIDOS,
                           hoy=date.today().isoformat(), elegido=elegido)


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
