"""Panel de administración: números del sitio y lista de cuentas.

No muestra el contenido de los vehículos ni los archivos de nadie (la política de privacidad dice que
solo los ve su dueño): solo cantidades, fechas y espacio usado. Para dar o quitar el rango:
python tools/admin.py <usuario> [--quitar]
"""
import glob
import sys
from collections import Counter

import respaldos
from nucleo import *  # noqa: F401,F403


def tamanio(ruta):
    try:
        return os.path.getsize(ruta)
    except OSError:
        return 0


def tamanio_carpeta(carpeta):
    total = n = 0
    for raiz, _, nombres in os.walk(carpeta):
        for nombre in nombres:
            total += tamanio(os.path.join(raiz, nombre))
            n += 1
    return total, n


@app.route("/admin")
@requiere_admin
def admin():
    db = get_db()
    hoy = date.today()
    uno = lambda sql, *p: db.execute(sql, p).fetchone()[0]  # noqa: E731
    totales = {
        "usuarios": uno("SELECT COUNT(*) FROM usuarios"),
        "vehiculos": uno("SELECT COUNT(*) FROM vehiculos"),
        "registros": uno("SELECT COUNT(*) FROM registros"),
        "pendientes": uno("SELECT COUNT(*) FROM pendientes"),
        "archivos": uno("SELECT COUNT(*) FROM archivos"),
        "bytes": uno("SELECT COALESCE(SUM(bytes), 0) FROM archivos"),
        "gasto": uno("SELECT COALESCE(SUM(costo), 0) FROM registros"),
        "activos_7": uno("SELECT COUNT(*) FROM usuarios WHERE actividad >= ?", (hoy - timedelta(days=7)).isoformat()),
        "activos_30": uno("SELECT COUNT(*) FROM usuarios WHERE actividad >= ?", (hoy - timedelta(days=30)).isoformat()),
        "calendarios": uno("SELECT COUNT(*) FROM usuarios WHERE cal_token IS NOT NULL"),
        "compartidos": uno("SELECT COUNT(*) FROM vehiculos WHERE share_token IS NOT NULL"),
    }
    # Cuentas nuevas por semana (las últimas 8).
    altas = Counter()
    for (creado,) in db.execute("SELECT creado FROM usuarios"):
        try:
            d = date.fromisoformat((creado or "")[:10])
        except ValueError:
            continue
        semanas = (hoy - d).days // 7
        if 0 <= semanas < 8:
            altas[semanas] += 1
    semanas = [{"desde": hoy - timedelta(days=7 * k + 6), "hasta": hoy - timedelta(days=7 * k), "n": altas[k]}
               for k in range(7, -1, -1)]
    tope = max([s["n"] for s in semanas] + [1])

    usuarios = db.execute("""
        SELECT u.id, u.usuario, u.creado, u.actividad, u.admin, u.foto IS NOT NULL AS con_foto,
               u.cal_token IS NOT NULL AS con_calendario,
               (SELECT COUNT(*) FROM vehiculos v WHERE v.usuario_id = u.id) AS vehiculos,
               (SELECT COUNT(*) FROM registros r JOIN vehiculos v ON v.id = r.vehiculo_id WHERE v.usuario_id = u.id) AS registros,
               (SELECT COUNT(*) FROM pendientes p JOIN vehiculos v ON v.id = p.vehiculo_id WHERE v.usuario_id = u.id) AS pendientes,
               (SELECT COALESCE(SUM(a.bytes), 0) FROM archivos a JOIN vehiculos v ON v.id = a.vehiculo_id WHERE v.usuario_id = u.id) AS bytes
        FROM usuarios u ORDER BY COALESCE(u.actividad, u.creado) DESC, u.id DESC""").fetchall()
    usuarios = [dict(u) for u in usuarios]
    for u in usuarios:
        try:
            u["dias"] = (hoy - date.fromisoformat(u["actividad"])).days
        except (TypeError, ValueError):
            u["dias"] = None
    marcas = db.execute("SELECT marca, COUNT(*) AS n FROM vehiculos WHERE COALESCE(marca, '') <> '' "
                        "GROUP BY marca ORDER BY n DESC, marca LIMIT 10").fetchall()
    categorias = [(CATEGORIAS.get(c, c), n) for c, n in db.execute(
        "SELECT categoria, COUNT(*) AS n FROM registros GROUP BY categoria ORDER BY n DESC").fetchall()]

    carpeta_resp = respaldos.carpeta_de(DB_PATH)
    copias = sorted(glob.glob(os.path.join(carpeta_resp, "bitacora-*.db")))
    subidos, n_subidos = tamanio_carpeta(archivos.CARPETA)
    sistema = {
        "base": tamanio(DB_PATH), "subidos": subidos, "n_subidos": n_subidos,
        "respaldos": len(copias), "ultimo_respaldo": os.path.basename(copias[-1])[9:19] if copias else None,
        "python": sys.version.split()[0],
    }
    return render_template("admin.html", totales=totales, semanas=semanas, tope=tope, usuarios=usuarios,
                           marcas=marcas, categorias=categorias, sistema=sistema, hoy=hoy)
