"""Plan de mantenimiento estimado según cuánto se usa el auto, y vencimientos
de documentación (VTV, seguro, patente…).

No toca la base de datos: recibe filas ya leídas y devuelve qué está vencido,
qué está cerca y qué está al día.
"""
import calendar
import unicodedata
from datetime import date, timedelta

DIAS_MES = 30.44

# Perfiles de uso: (nombre, km por mes, descripción).
USOS = {
    "poco": ("Manejo poco", 500, "Hasta ~6.000 km por año: salidas cortas y fines de semana."),
    "promedio": ("Manejo promedio", 1250, "~15.000 km por año: uso diario normal."),
    "mucho": ("Manejo mucho", 2500, "~30.000 km por año o más: ruta, trabajo, aplicaciones."),
    # Los km por mes los pone la persona (columna km_mes).
    "personalizado": ("Personalizado", None, "Elegí vos cuántos km hacés por mes."),
}
KM_MES_MAX = 30000

# Services más importantes: (clave, nombre, cada km, cada meses, palabras del título,
# combustibles a los que NO aplica). Intervalos generales y conservadores: el
# manual de cada auto manda.
PLAN = [
    ("aceite", "Aceite y filtro de aceite", 10000, 12, ["aceite"], {"electrico"}),
    ("filtro_aire", "Filtro de aire", 20000, 24, ["filtro de aire"], {"electrico"}),
    ("filtro_habitaculo", "Filtro de habitáculo", 15000, 12,
     ["habitaculo", "filtro de polen", "filtro de cabina", "filtro antipolen"], set()),
    ("filtro_combustible", "Filtro de combustible", 30000, 24,
     ["filtro de combustible", "filtro de nafta", "filtro de gasoil"], {"electrico"}),
    ("bujias", "Bujías", 30000, 36, ["bujia"], {"diesel", "electrico"}),
    ("liquido_frenos", "Líquido de frenos", 40000, 24, ["liquido de freno"], set()),
    ("refrigerante", "Líquido refrigerante", 40000, 24, ["refrigerante", "anticongelante"], set()),
    ("distribucion", "Correa de distribución", 60000, 48, ["distribucion"], {"electrico"}),
    ("alineacion", "Alineación, balanceo y rotación", 10000, 12,
     ["alineacion", "balanceo", "rotacion"], set()),
    ("frenos", "Revisión de frenos (pastillas y discos)", 20000, 12,
     ["pastilla", "disco de freno", "discos de freno", "revision de frenos", "frenos"], set()),
]

DOCUMENTOS = {
    "vtv": "VTV / RTO",
    "seguro": "Póliza del seguro",
    "seguro_pago": "Pago del seguro",
    "matafuego": "Matafuegos",
    "patente": "Patente / impuesto automotor",
    "registro": "Registro de conducir",
}
# Cada cuántos meses se repite cada documento, para sugerir en el formulario.
REPETICION_SUGERIDA = {"vtv": 12, "seguro": 12, "seguro_pago": 1, "matafuego": 12,
                       "patente": 2, "registro": None}
REPETICIONES = {1: "Todos los meses", 2: "Cada 2 meses", 3: "Cada 3 meses", 6: "Cada 6 meses",
                12: "Cada año", 24: "Cada 2 años", 60: "Cada 5 años"}


def norm(texto):
    t = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def a_fecha(iso):
    try:
        return date.fromisoformat(iso or "")
    except ValueError:
        return None


def sumar_meses(d, meses):
    m = d.month - 1 + meses
    anio, mes = d.year + m // 12, m % 12 + 1
    return date(anio, mes, min(d.day, calendar.monthrange(anio, mes)[1]))


def km_por_mes(v):
    """Km por mes del perfil de uso del vehículo (el elegido, o el que cargó a mano)."""
    uso = v["uso"]
    if uso == "personalizado":
        n = v["km_mes"]
        return n if isinstance(n, int) and 0 < n <= KM_MES_MAX else None
    return USOS[uso][1] if uso in USOS else None


def promedio_medido(registros):
    """Km por mes según los registros cargados (necesita ~2 meses de historia)."""
    puntos = sorted((d, r["km"]) for r in registros
                    if r["km"] and (d := a_fecha(r["fecha"])))
    if len(puntos) < 2:
        return None
    (d0, k0), (d1, k1) = puntos[0], puntos[-1]
    dias = (d1 - d0).days
    if dias < 60 or k1 <= k0:
        return None
    return round((k1 - k0) / (dias / DIAS_MES))


def km_estimado(v, registros, hoy=None):
    """Km de hoy: el último km conocido más lo que se estima que se manejó desde
    entonces según el perfil de uso. Sin perfil, el último km conocido."""
    hoy = hoy or date.today()
    conocidos = [(r["km"], a_fecha(r["fecha"])) for r in registros if r["km"]]
    if v["km_inicial"]:
        conocidos.append((v["km_inicial"], a_fecha((v["creado"] or "")[:10])))
    if v["km_manual"]:  # kilometraje que el dueño anotó a mano, sin cargar un registro
        conocidos.append((v["km_manual"], a_fecha(v["km_manual_fecha"] or "")))
    if not conocidos:
        return 0
    km, cuando = max(conocidos, key=lambda x: x[0])
    kpm = km_por_mes(v)
    if not kpm or not cuando or cuando >= hoy:
        return km
    return km + round(kpm * (hoy - cuando).days / DIAS_MES)


def estado(dias, faltan_km=None, aviso_dias=30):
    if dias <= 0 or (faltan_km is not None and faltan_km <= 0):
        return "vencido"
    if dias <= aviso_dias or (faltan_km is not None and faltan_km <= 1000):
        return "pronto"
    return "ok"


def plan_mantenimiento(v, registros, hoy=None):
    """Para cada service del plan: último registro que lo menciona y cuándo toca
    el próximo, por km (estimados con el perfil de uso) o por tiempo."""
    if "carroceria" in v.keys() and v["carroceria"] == "moto":
        return []  # Los intervalos del plan son de autos; la moto usa los controles de su manual.
    kpm = km_por_mes(v)
    if not kpm:
        return []
    hoy = hoy or date.today()
    km_hoy = km_estimado(v, registros, hoy)
    items = []
    for clave, nombre, cada_km, cada_meses, palabras, no_aplica in PLAN:
        if v["combustible"] in no_aplica:
            continue
        ultimo = None
        for r in registros:  # vienen del más nuevo al más viejo
            if r["categoria"] != "reparacion" and any(p in norm(r["titulo"]) for p in palabras):
                ultimo = r
                break
        item = {"clave": clave, "nombre": nombre, "cada_km": cada_km, "cada_meses": cada_meses,
                "ultimo": ultimo}
        desde = a_fecha(ultimo["fecha"]) if ultimo else None
        if not desde:
            item["estado"] = "sin_dato"
            items.append(item)
            continue
        por_tiempo = sumar_meses(desde, cada_meses)
        proximo_km = faltan_km = None
        cuando = por_tiempo
        if ultimo["km"]:
            proximo_km = ultimo["km"] + cada_km
            faltan_km = proximo_km - km_hoy
            por_km = hoy + timedelta(days=round(faltan_km / kpm * DIAS_MES))
            cuando = min(por_tiempo, por_km)
        dias = (cuando - hoy).days
        total = max(1, (cuando - desde).days)
        item.update(estado=estado(dias, faltan_km), fecha=cuando.isoformat(), dias=dias,
                    proximo_km=proximo_km, faltan_km=faltan_km,
                    progreso=min(1.0, max(0.0, (hoy - desde).days / total)))
        items.append(item)
    orden = {"vencido": 0, "pronto": 1, "ok": 2, "sin_dato": 3}
    items.sort(key=lambda x: (orden[x["estado"]], x.get("dias", 0)))
    return items


def vencimientos(documentos, hoy=None):
    """Documentos con fecha: cuántos días faltan y su estado. Los pagos mensuales
    avisan una semana antes; el resto, un mes antes."""
    hoy = hoy or date.today()
    salida = []
    for d in documentos:
        vence = a_fecha(d["vence"])
        if not vence:  # solo con detalle (compañía, n.º de póliza…): se muestra sin aviso
            salida.append({"doc": d, "nombre": DOCUMENTOS.get(d["tipo"], d["tipo"]), "dias": None,
                           "estado": "sin_fecha"})
            continue
        dias = (vence - hoy).days
        aviso = 7 if d["cada_meses"] == 1 else 30
        salida.append({"doc": d, "nombre": DOCUMENTOS.get(d["tipo"], d["tipo"]), "dias": dias,
                       "estado": "vencido" if dias < 0 else estado(dias + 1, None, aviso)})
    orden = list(DOCUMENTOS)
    salida.sort(key=lambda x: (x["dias"] is None, x["dias"] or 0,
                               orden.index(x["doc"]["tipo"]) if x["doc"]["tipo"] in orden else 99))
    return salida
