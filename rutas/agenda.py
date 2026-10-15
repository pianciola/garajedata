"""Calendario dentro de la página: los próximos controles anotados en los registros, los services
estimados del plan y los vencimientos de papeles de todos los vehículos, mes por mes."""
import calendar

from mantenimiento import DIAS_MES, sumar_meses
from nucleo import *  # noqa: F401,F403

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
DIAS_LARGOS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
ANIOS_ATRAS, ANIOS_ADELANTE = 2, 5  # el calendario muestra desde hace 2 años hasta dentro de 5
TIPOS = {"control": "Control", "plan": "Service estimado", "doc": "Vencimiento"}


def agenda_de(uid, hasta):
    """Todo lo que viene (o ya pasó sin hacerse) en los vehículos del usuario, como una lista de eventos.
    Los vencimientos que se repiten (VTV anual, cuota mensual…) se proyectan hasta «hasta»."""
    hoy = date.today()
    eventos = []
    vehiculos = get_db().execute("SELECT * FROM vehiculos WHERE usuario_id = ? ORDER BY orden, id", (uid,)).fetchall()
    for v in vehiculos:
        a = avisos(v)
        base = {"vid": v["id"], "auto": nombre_auto(v), "color": v["color"] or COLOR_DEFAULT}
        kpm = km_por_mes(v) or 1250
        for r in a["recordatorios"]:
            reg = r["registro"]
            fechas = []
            if r["faltan_dias"] is not None:
                fechas.append((hoy + timedelta(days=r["faltan_dias"]), False))
            if r["faltan_km"] is not None:
                fechas.append((hoy + timedelta(days=round(r["faltan_km"] / kpm * DIAS_MES)), True))
            if not fechas:
                continue
            fecha, estimado = min(fechas)
            if estimado and fecha < hoy:
                fecha = hoy  # pasado de km: se muestra hoy
            detalle = []
            if reg["prox_km"]:
                detalle.append(f"a los {miles(reg['prox_km'])} km")
            if reg["prox_fecha"]:
                detalle.append(f"o el {fecha_ar(reg['prox_fecha'])}" if detalle else f"el {fecha_ar(reg['prox_fecha'])}")
            eventos.append(dict(base, tipo="control", fecha=fecha, estimado=estimado, estado=r["estado"],
                                titulo=reg["titulo"], detalle=("Anotado para " + " ".join(detalle)) if detalle else ""))
        for p in a["plan"]:
            if not p.get("fecha"):
                continue
            eventos.append(dict(base, tipo="plan", fecha=max(hoy, date.fromisoformat(p["fecha"])), estimado=True,
                                estado=p["estado"], titulo=p["nombre"],
                                detalle=f"Según el plan: cada {miles(p['cada_km'])} km o {p['cada_meses']} meses"))
        for d in a["documentos"]:
            if d["dias"] is None:
                continue
            vence = date.fromisoformat(d["doc"]["vence"])
            eventos.append(dict(base, tipo="doc", fecha=vence, estimado=False, estado=d["estado"],
                                titulo=d["nombre"], detalle=d["doc"]["detalle"] or ""))
            cada = d["doc"]["cada_meses"]
            if cada:
                for n in range(1, 61):
                    siguiente = sumar_meses(vence, cada * n)
                    if siguiente > hasta:
                        break
                    if siguiente >= hoy:
                        eventos.append(dict(base, tipo="doc", fecha=siguiente, estimado=False, estado="ok",
                                            titulo=d["nombre"], detalle="Se repite", repetido=True))
    eventos.sort(key=lambda e: (e["fecha"], {"vencido": 0, "pronto": 1}.get(e["estado"], 2), e["auto"]))
    return eventos


def fecha_ar(iso):
    try:
        return date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return iso


def dia_largo(d):
    return f"{DIAS_LARGOS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


@app.route("/calendario")
@requiere_login
def agenda():
    hoy = date.today()
    anio_min, anio_max = hoy.year - ANIOS_ATRAS, hoy.year + ANIOS_ADELANTE
    anio, mes = hoy.year, hoy.month
    # Se pide como ?mes=2026-12 (flechas) o ?a=2026&m=12 (desplegables). Lo que no encaja se ignora
    # y un año fuera del rango se lleva al borde más cercano.
    pedido = request.args.get("mes", "")
    a = m = None
    if re.fullmatch(r"\d{4}-\d{2}", pedido):
        a, m = int(pedido[:4]), int(pedido[5:])
    elif re.fullmatch(r"\d{4}", request.args.get("a", "")) and re.fullmatch(r"\d{1,2}", request.args.get("m", "")):
        a, m = int(request.args["a"]), int(request.args["m"])
    if a is not None and 1 <= m <= 12:
        if a < anio_min:
            a, m = anio_min, 1
        elif a > anio_max:
            a, m = anio_max, 12
        anio, mes = a, m
    semanas = calendar.Calendar(0).monthdatescalendar(anio, mes)
    eventos = agenda_de(g.usuario["id"], hasta=max(semanas[-1][-1], hoy))
    por_dia = {}
    for e in eventos:
        por_dia.setdefault(e["fecha"], []).append(e)
    atrasados = [e for e in eventos if e["estado"] == "vencido"]
    del_mes = [(d, por_dia[d]) for d in sorted(por_dia) if d.year == anio and d.month == mes]
    anterior = date(anio, mes, 1) - timedelta(days=1)
    siguiente = date(anio, mes, 28) + timedelta(days=7)
    proximo = next((e for e in eventos if e["fecha"] >= hoy and e["estado"] != "vencido"), None)
    return render_template("calendario.html", semanas=semanas, por_dia=por_dia, hoy=hoy, anio=anio, mes=mes,
                           nombre_mes=MESES[mes - 1], dias_semana=DIAS_SEMANA, atrasados=atrasados,
                           del_mes=del_mes, tipos=TIPOS, dia_largo=dia_largo, proximo=proximo,
                           mes_anterior=f"{anterior.year}-{anterior.month:02d}",
                           mes_siguiente=f"{siguiente.year}-{siguiente.month:02d}",
                           es_hoy=(anio == hoy.year and mes == hoy.month), meses=MESES,
                           anios=range(anio_min, anio_max + 1),
                           hay_anterior=(anio, mes) > (anio_min, 1), hay_siguiente=(anio, mes) < (anio_max, 12),
                           hay_autos=bool(get_db().execute("SELECT 1 FROM vehiculos WHERE usuario_id = ?",
                                                           (g.usuario["id"],)).fetchone()))
