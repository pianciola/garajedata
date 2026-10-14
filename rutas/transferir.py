"""Pasar un vehículo, con toda su historia, a otra cuenta (por ejemplo, al venderlo)."""
from nucleo import *  # noqa: F401,F403

HORAS_TRANSFERENCIA = 72


@app.route("/vehiculo/<int:vid>/transferir", methods=["GET", "POST"])
@requiere_login
def transferir(vid):
    v = get_vehiculo(vid)
    codigo = None
    if request.method == "POST":
        if request.form.get("accion") == "cancelar":
            get_db().execute("UPDATE vehiculos SET transfer_codigo = NULL, transfer_vence = NULL "
                             "WHERE id = ?", (vid,))
            get_db().commit()
            flash("Transferencia cancelada: el código ya no sirve.", "ok")
            return redirect(url_for("transferir", vid=vid))
        codigo = "".join(secrets.choice(ALFABETO) for _ in range(12))
        vence = (datetime.now() + timedelta(hours=HORAS_TRANSFERENCIA)).isoformat(timespec="seconds")
        get_db().execute("UPDATE vehiculos SET transfer_codigo = ?, transfer_vence = ? WHERE id = ?",
                         (generate_password_hash(codigo), vence, vid))
        get_db().commit()
        v = get_vehiculo(vid)
    pendiente = bool(v["transfer_codigo"] and (v["transfer_vence"] or "") > datetime.now().isoformat())
    return render_template("transferir.html", v=v, codigo=codigo, pendiente=pendiente,
                           horas=HORAS_TRANSFERENCIA)


@app.route("/recibir", methods=["GET", "POST"])
@requiere_login
def recibir():
    if request.method == "POST":
        llave = "recibir:" + str(g.usuario["id"])
        if bloqueado(llave):
            flash("Demasiados intentos. Esperá unos minutos.", "error")
            return render_template("recibir.html"), 429
        codigo = normalizar_codigo(request.form.get("codigo", ""))
        db = get_db()
        candidatos = db.execute("SELECT * FROM vehiculos WHERE transfer_codigo IS NOT NULL "
                                "AND transfer_vence > ?",
                                (datetime.now().isoformat(timespec="seconds"),)).fetchall()
        v = next((c for c in candidatos
                  if len(codigo) == 12 and check_password_hash(c["transfer_codigo"], codigo)), None)
        if v is None:
            INTENTOS.setdefault(llave, []).append(time.time())
            flash("Ese código no existe o ya venció.", "error")
        elif v["usuario_id"] == g.usuario["id"]:
            flash("Ese vehículo ya es tuyo.", "error")
        else:
            peso = db.execute("SELECT COALESCE(SUM(bytes), 0) FROM archivos WHERE vehiculo_id = ?",
                              (v["id"],)).fetchone()[0]
            if espacio_usado() + peso > archivos.CUPO_USUARIO:
                flash("No te alcanza el espacio de la cuenta (100 MB) para los archivos de ese "
                      "vehículo. Borrá algo de tu bóveda y probá de nuevo.", "error")
            else:
                ultimo = db.execute("SELECT MAX(orden) FROM vehiculos WHERE usuario_id = ?",
                                    (g.usuario["id"],)).fetchone()[0]
                # Pasa con toda su historia; el link de solo lectura del dueño anterior deja de andar.
                # El UPDATE solo prospera si el código sigue vigente: si dos personas lo canjean a la vez,
                # una sola se queda con el auto.
                cur = db.execute("UPDATE vehiculos SET usuario_id = ?, orden = ?, share_token = NULL, "
                                 "transfer_codigo = NULL, transfer_vence = NULL "
                                 "WHERE id = ? AND transfer_codigo = ? AND usuario_id = ?",
                                 (g.usuario["id"], (ultimo or 0) + 1, v["id"], v["transfer_codigo"], v["usuario_id"]))
                db.commit()
                if cur.rowcount != 1:
                    flash("Ese código ya fue usado.", "error")
                    return render_template("recibir.html"), 200
                flash(f"¡Listo! {nombre_auto(v)} ya está en tu garaje, con toda su historia.", "ok")
                return redirect(url_for("vehiculo", vid=v["id"]))
    return render_template("recibir.html")
