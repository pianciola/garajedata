"""Lista de vehículos, ficha, alta, edición, documentación."""
from flask import jsonify

from consejos import CATEGORIAS as CATEGORIAS_CONSEJO, PREFERENCIAS_DATOS, consejo_del_dia
from nucleo import *  # noqa: F401,F403


def preferencia_datos():
    """Qué datos de garaje quiere ver la cuenta conectada (todos, si no hay cuenta)."""
    pref = g.usuario["datos_garaje"] if g.usuario else None
    return pref if pref in PREFERENCIAS_DATOS else "todos"


@app.route("/consejo/<int:salto>")
def consejo_json(salto):
    """Otro consejo (el de hoy desplazado «salto» lugares), para el botón «Otro» del inicio."""
    i, categoria, texto = consejo_del_dia(salto=min(salto, 10_000), preferencia=preferencia_datos())
    resp = jsonify({"i": i, "categoria": CATEGORIAS_CONSEJO[categoria], "clave": categoria, "texto": texto})
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/consejos/<int:desde>")
def consejos_tanda(desde):
    """Los próximos 40 consejos desde el lugar «desde»: el navegador elige el primero que no haya visto."""
    desde = min(desde, 10_000)
    tanda = []
    for salto in range(desde, desde + 40):
        i, categoria, texto = consejo_del_dia(salto=salto, preferencia=preferencia_datos())
        tanda.append({"salto": salto, "i": i, "categoria": CATEGORIAS_CONSEJO[categoria], "clave": categoria, "texto": texto})
    resp = jsonify(tanda)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/")
def index():
    if g.usuario is None:
        return render_template("bienvenida.html")
    vehiculos = get_db().execute("""
        SELECT v.*, COUNT(r.id) AS n, MAX(r.fecha) AS ultimo,
               MAX(r.km) AS max_km
        FROM vehiculos v LEFT JOIN registros r ON r.vehiculo_id = v.id
        WHERE v.usuario_id = ?
        GROUP BY v.id
        ORDER BY v.orden IS NULL, v.orden,
                 COALESCE(NULLIF(v.nombre, ''), v.marca || ' ' || v.modelo) COLLATE NOCASE
    """, (g.usuario["id"],)).fetchall()
    alertas, cartel, proximos = {}, [], {}
    for v in vehiculos:
        a = avisos(v)
        alertas[v["id"]] = contar_avisos(a)
        proximos[v["id"]] = proximo_control(v, a)
        cartel += lista_avisos(v, a, con_nombre=len(vehiculos) > 1)
    cartel.sort(key=lambda x: x["estado"] != "vencido")
    i, categoria, texto = consejo_del_dia(preferencia=preferencia_datos())
    consejo ={"i": i, "clave": categoria, "categoria": CATEGORIAS_CONSEJO[categoria], "texto": texto}
    return render_template("index.html", vehiculos=vehiculos, alertas=alertas, cartel=[], proximos=proximos,
                           pendientes=cartel, consejo=consejo,
                           vencidos=sum(p["estado"] == "vencido" for p in cartel))


@app.post("/vehiculos/orden")
@requiere_login
def vehiculos_orden():
    """Guarda el orden elegido para la lista de vehículos (ids separados por coma)."""
    db = get_db()
    propios = {r["id"] for r in db.execute("SELECT id FROM vehiculos WHERE usuario_id = ?", (g.usuario["id"],))}
    pedidos = [to_int(x) for x in request.form.get("ids", "").split(",")]
    ids = [i for i in dict.fromkeys(pedidos) if i in propios]
    resto = sorted(propios - set(ids))
    for n, vid in enumerate(ids + resto, 1):
        db.execute("UPDATE vehiculos SET orden = ? WHERE id = ? AND usuario_id = ?", (n, vid, g.usuario["id"]))
    db.commit()
    return ("", 204)


@app.route("/vehiculo/nuevo", methods=["GET", "POST"])
@requiere_login
def vehiculo_nuevo():
    if request.method == "POST":
        d = datos_vehiculo_form()
        ultimo = get_db().execute("SELECT MAX(orden) FROM vehiculos WHERE usuario_id = ?",
                                  (g.usuario["id"],)).fetchone()[0]
        d.update(usuario_id=g.usuario["id"], creado=date.today().isoformat(),
                 orden=(ultimo or 0) + 1)
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
        cat=cat, q=q, anio=anio, espacio=espacio_usado(), cartel=lista_avisos(v, a),
        boveda_cat=request.args.get("boveda"), proximo=proximo_control(v, a))


@app.post("/vehiculo/<int:vid>/km")
@requiere_login
def vehiculo_km(vid):
    """Actualiza el odómetro sin tener que cargar un registro de mantenimiento."""
    v = get_vehiculo(vid)
    km = to_int(request.form.get("km"))
    if km is None:
        flash("Escribí el kilometraje que marca hoy el auto.", "error")
    elif km < km_actual(v):
        flash(f"El auto ya tiene cargados {miles(km_actual(v))} km: el odómetro no puede bajar. "
              "Si te equivocaste antes, corregí el registro o el km inicial.", "error")
    else:
        get_db().execute("UPDATE vehiculos SET km_manual = ?, km_manual_fecha = ? WHERE id = ?",
                         (km, date.today().isoformat(), vid))
        get_db().commit()
        flash(f"Odómetro actualizado: {miles(km)} km.", "ok")
    return redirect(url_for("vehiculo", vid=vid))


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


@app.route("/vehiculo/<int:vid>/foto", methods=["POST"])
@requiere_login
def vehiculo_foto(vid):
    """Cambiar o ajustar la foto del auto directo desde la ficha, sin pasar por todo el formulario."""
    get_vehiculo(vid)
    d = datos_foto_form()
    d["id"] = vid
    get_db().execute("UPDATE vehiculos SET imagen_modo = :imagen_modo, foto_x = :foto_x, foto_y = :foto_y, "
                     "foto_zoom = :foto_zoom, foto_ajuste = :foto_ajuste WHERE id = :id", d)
    get_db().commit()
    guardar_portada(vid)
    flash("Imagen del auto actualizada.", "ok")
    return redirect(url_for("vehiculo", vid=vid))


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
            # un vencimiento puede estar ya vencido, pero no de hace años
            vence = to_fecha(request.form.get(f"vence_{tipo}"), minimo=date.today() - timedelta(days=365))
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
