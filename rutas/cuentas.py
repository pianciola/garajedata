"""Cuentas: registro, ingreso, recuperación y ajustes."""
from consejos import PREFERENCIAS_DATOS
from nucleo import *  # noqa: F401,F403


@app.route("/registro", methods=["GET", "POST"])
def registrarse():
    if g.usuario:
        return redirect(url_for("index"))
    nombre = ""
    if request.method == "POST":
        nombre = request.form.get("usuario", "").strip()
        clave = request.form.get("clave", "")
        error = motivo_sin_altas()
        if error:
            flash(error, "error")
            return render_template("registro.html", nombre=nombre), 429
        if not request.form.get("acepto"):
            error = "Para crear la cuenta tenés que aceptar los Términos y la Política de privacidad."
        elif not re.fullmatch(r"[A-Za-z0-9._-]{3,30}", nombre):
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
                ALTAS_IP.setdefault(ip_cliente(), []).append(time.time())
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
        nombre = request.form.get("usuario", "").strip()[:60]
        if ingreso_bloqueado(nombre):
            flash("Demasiados intentos. Esperá unos minutos y probá de nuevo.", "error")
            return render_template("login.html", nombre=nombre), 429
        u = get_db().execute("SELECT * FROM usuarios WHERE usuario = ?", (nombre,)).fetchone()
        clave = request.form.get("clave", "")
        # Siempre se calcula un hash (aunque el usuario no exista o la clave sea absurda): ni el tiempo
        # de respuesta delata qué usuarios existen, ni una clave de megas gasta CPU.
        correcta = check_password_hash(u["clave"] if u else CLAVE_FALSA, clave[:200])
        if u and correcta and len(clave) <= 200:
            ingreso_ok(nombre)
            iniciar_sesion(u["id"])
            return redirect(destino_seguro())
        ingreso_fallido(nombre)
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
        nombre = request.form.get("usuario", "").strip()[:60]
        if ingreso_bloqueado(nombre):
            flash("Demasiados intentos. Esperá unos minutos y probá de nuevo.", "error")
            return render_template("recuperar.html", nombre=nombre), 429
        u = get_db().execute("SELECT * FROM usuarios WHERE usuario = ?", (nombre,)).fetchone()
        codigo = normalizar_codigo(request.form.get("codigo"))[:64]
        valido = check_password_hash(u["codigo"] if u and u["codigo"] else CLAVE_FALSA, codigo)
        if not (u and u["codigo"] and valido):
            ingreso_fallido(nombre)
            flash("Usuario o código incorrectos.", "error")
            return render_template("recuperar.html", nombre=nombre)
        error = validar_clave(request.form.get("clave", ""), request.form.get("clave2", ""))
        if error:
            flash(error, "error")
            return render_template("recuperar.html", nombre=nombre)
        get_db().execute("UPDATE usuarios SET clave = ? WHERE id = ?",
                         (generate_password_hash(request.form["clave"]), u["id"]))
        ingreso_ok(nombre)
        invalidar_sesiones(u["id"])
        iniciar_sesion(u["id"])
        # El código usado ya no sirve: se entrega uno nuevo.
        nuevo_codigo(u["id"])
        flash("Contraseña cambiada. Guardá tu nuevo código de recuperación.", "ok")
        return redirect(url_for("codigo"))
    return render_template("recuperar.html", nombre=nombre)


@app.post("/cuenta/foto")
@requiere_login
def cuenta_foto():
    """Sube o quita la foto de perfil (la ve solo su dueño: en la barra y en Mi cuenta)."""
    db = get_db()
    anterior = g.usuario["foto"]
    if request.form.get("accion") == "quitar":
        nueva = None
        flash("Foto de perfil quitada.", "ok")
    else:
        try:
            nueva = archivos.guardar_avatar(request.files.get("foto") or io.BytesIO(b""))
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("cuenta"))
        flash("Foto de perfil actualizada.", "ok")
    db.execute("UPDATE usuarios SET foto = ? WHERE id = ?", (nueva, g.usuario["id"]))
    db.commit()
    if anterior:
        archivos.borrar([anterior])
    return redirect(url_for("cuenta"))


@app.get("/cuenta/foto")
@requiere_login
def cuenta_foto_ver():
    if not g.usuario["foto"] or not os.path.isfile(archivos.ruta(g.usuario["foto"])):
        abort(404)
    resp = send_file(archivos.ruta(g.usuario["foto"]), mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "private, max-age=86400"
    return resp


@app.post("/cuenta/datos-garaje")
@requiere_login
def cuenta_datos_garaje():
    """Qué datos de garaje ve la cuenta: todos, o sin los de moto, o sin los de auto."""
    elegido = request.form.get("datos", "")
    if elegido not in PREFERENCIAS_DATOS:
        flash("Elegí una de las opciones de la lista.", "error")
    else:
        db = get_db()
        db.execute("UPDATE usuarios SET datos_garaje = ? WHERE id = ?", (elegido, g.usuario["id"]))
        db.commit()
        flash("Preferencia guardada.", "ok")
    return redirect(url_for("cuenta") + "#preferencias")


@app.route("/cuenta", methods=["GET", "POST"])
@requiere_login
def cuenta():
    if request.method == "POST":
        u = get_db().execute("SELECT * FROM usuarios WHERE id = ?", (g.usuario["id"],)).fetchone()
        if not check_password_hash(u["clave"], request.form.get("actual", "")):
            flash("La contraseña actual no es correcta.", "error")
        elif request.form.get("accion") == "borrar":
            if request.form.get("confirmar", "").strip().lower() != u["usuario"].lower():
                flash("Para borrar la cuenta escribí tu usuario exactamente.", "error")
            else:
                db = get_db()
                nombres = [r[0] for r in db.execute(
                    "SELECT a.archivo FROM archivos a JOIN vehiculos v ON v.id = a.vehiculo_id "
                    "WHERE v.usuario_id = ?", (u["id"],))]
                if u["foto"]:
                    nombres.append(u["foto"])
                db.execute("DELETE FROM vehiculos WHERE usuario_id = ?", (u["id"],))
                db.execute("DELETE FROM usuarios WHERE id = ?", (u["id"],))
                db.commit()
                archivos.borrar(nombres)
                session.clear()
                flash("Tu cuenta y todos sus datos se borraron.", "ok")
                return redirect(url_for("index"))
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
                invalidar_sesiones(u["id"])
                iniciar_sesion(u["id"])
                flash("Contraseña cambiada.", "ok")
                return redirect(url_for("cuenta"))
    cal = get_db().execute("SELECT cal_token FROM usuarios WHERE id = ?", (g.usuario["id"],)).fetchone()[0]
    return render_template("cuenta.html", cal_link=url_absoluta("calendario", token=cal) if cal else None,
                           preferencias=PREFERENCIAS_DATOS, pref_datos=g.usuario["datos_garaje"])


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


@app.post("/logout")
def logout():
    sid = session.get("sid")
    if isinstance(sid, str):
        get_db().execute("DELETE FROM sesiones WHERE token = ?", (hashlib.sha256(sid.encode()).hexdigest(),))
        get_db().commit()
    session.clear()
    return redirect(url_for("index"))
