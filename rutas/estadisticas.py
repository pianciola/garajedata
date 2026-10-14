"""Estadísticas de gasto y uso de un vehículo."""
from nucleo import *  # noqa: F401,F403


@app.route("/vehiculo/<int:vid>/estadisticas")
@requiere_login
def estadisticas(vid):
    v = get_vehiculo(vid)
    regs = get_db().execute("SELECT * FROM registros WHERE vehiculo_id = ? ORDER BY fecha, km, id",
                            (vid,)).fetchall()
    hoy = date.today()
    # Gasto de los últimos 12 meses, mes por mes (los meses sin gasto quedan en cero).
    meses = []
    for i in range(11, -1, -1):
        d = sumar_meses(hoy.replace(day=1), -i)
        meses.append({"clave": d.strftime("%Y-%m"), "etiqueta": d.strftime("%m/%y"), "total": 0.0})
    por_mes = {m["clave"]: m for m in meses}
    por_cat = {}
    total = 0.0
    for r in regs:
        costo = r["costo"] or 0
        total += costo
        por_cat[r["categoria"]] = por_cat.get(r["categoria"], 0) + costo
        if r["fecha"][:7] in por_mes:
            por_mes[r["fecha"][:7]]["total"] += costo
    cats = sorted(((CATEGORIAS.get(k, k), k, t) for k, t in por_cat.items() if t), key=lambda x: -x[2])
    # Costo por km: lo gastado dividido los km que se registraron.
    kms = [r["km"] for r in regs if r["km"]] + ([v["km_inicial"]] if v["km_inicial"] else [])
    desde, hasta = (min(kms), km_actual(v)) if kms else (None, None)
    recorridos = hasta - desde if kms and hasta > desde else None
    meses_uso = None
    if regs:
        meses_uso = max(1, round((hoy - date.fromisoformat(regs[0]["fecha"])).days / 30.44))
    return render_template(
        "estadisticas.html", v=v, n=len(regs), total=total, meses=meses,
        max_mes=max([m["total"] for m in meses] + [1]), anio_total=sum(m["total"] for m in meses),
        cats=cats, max_cat=max([t for _, _, t in cats] + [1]), recorridos=recorridos,
        costo_km=(total / recorridos) if recorridos else None,
        por_mes_prom=round(total / meses_uso) if meses_uso else None,
        medido=promedio_medido(list(reversed(regs))) if regs else None)
