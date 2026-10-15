"""Estadísticas de gasto y uso de un vehículo."""
from nucleo import *  # noqa: F401,F403
import calendar


def resumen_gastos(regs, v, hoy):
    """Compara el mismo tramo del mes y usa sólo odómetros con fecha para el costo/km."""
    actual = hoy.replace(day=1)
    anterior = sumar_meses(actual, -1)
    corte = anterior.replace(day=min(hoy.day, calendar.monthrange(anterior.year, anterior.month)[1]))
    gastos = [dict(r) for r in regs if r["fecha"] <= hoy.isoformat()]
    suma = lambda inicio, fin: sum((r["costo"] or 0) for r in gastos if inicio <= r["fecha"] <= fin)
    mes = suma(actual.isoformat(), hoy.isoformat())
    previo = suma(anterior.isoformat(), corte.isoformat())
    lecturas = [(r["fecha"], r["km"]) for r in gastos if r["km"] is not None]
    if v["km_manual"] is not None and v["km_manual_fecha"] and v["km_manual_fecha"] <= hoy.isoformat():
        lecturas.append((v["km_manual_fecha"], v["km_manual"]))
    lecturas.sort()
    desde, hasta = lecturas[0] if lecturas else (None, None), lecturas[-1] if lecturas else (None, None)
    creciente = all(b[1] >= a[1] for a, b in zip(lecturas, lecturas[1:]))
    distancia = hasta[1] - desde[1] if desde[0] and creciente and hasta[0] > desde[0] and hasta[1] > desde[1] else None
    intervalo = [r for r in gastos if distancia and desde[0] < r["fecha"] <= hasta[0]]
    conocidos = [r for r in intervalo if r["costo"] is not None]
    incompletos = sum(r["costo"] is None for r in gastos)
    return dict(mes_actual=mes, mes_previo=previo, corte_previo=corte.isoformat(),
                diferencia=(mes-previo)/previo*100 if previo else None,
                sin_costo=incompletos, con_costo=len(gastos)-incompletos,
                costo_km=sum(r["costo"] for r in conocidos)/distancia if distancia and conocidos else None,
                recorridos=distancia, periodo_desde=desde[0], periodo_hasta=hasta[0],
                faltantes_intervalo=sum(r["costo"] is None for r in intervalo))


@app.route("/vehiculo/<int:vid>/estadisticas")
@requiere_login
def estadisticas(vid):
    v = get_vehiculo(vid)
    regs = get_db().execute("SELECT * FROM registros WHERE vehiculo_id = ? ORDER BY fecha, km, id",
                            (vid,)).fetchall()
    hoy = date.today()
    resumen = resumen_gastos(regs, v, hoy)
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
    meses_uso = None
    if regs:
        primera = date.fromisoformat(regs[0]["fecha"])
        meses_uso = max(1, (hoy.year - primera.year) * 12 + hoy.month - primera.month + 1)
    return render_template(
        "estadisticas.html", v=v, n=len(regs), total=total, meses=meses,
        max_mes=max([m["total"] for m in meses] + [1]), anio_total=sum(m["total"] for m in meses),
        cats=cats, max_cat=max([t for _, _, t in cats] + [1]), recorridos=resumen["recorridos"],
        costo_km=resumen["costo_km"], resumen=resumen, hoy=hoy,
        por_mes_prom=round(total / meses_uso) if meses_uso else None, meses_promedio=meses_uso,
        medido=promedio_medido(list(reversed(regs))) if regs else None)
