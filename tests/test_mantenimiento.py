"""Pruebas unitarias de mantenimiento.py: fechas, kilometrajes y estados, sin base de datos.

Es la lógica que decide cuándo toca cada service y qué está vencido; acá se prueban los bordes
que desde la página son difíciles de provocar (fines de mes, valores extremos, tipos de papel).
"""
import os
import sys
from datetime import date, timedelta

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mantenimiento import (DIAS_MAX, dias_por_km, estado, km_estimado, km_por_mes,  # noqa: E402
                           plan_mantenimiento, promedio_medido, sumar_meses, vencimientos)

HOY = date(2026, 10, 18)


def vehiculo(**datos):
    """Fila de vehículos con los campos que usa el plan (como la devuelve la base)."""
    base = {"carroceria": "sedan", "combustible": "nafta", "uso": None, "km_mes": None,
            "km_inicial": None, "creado": None, "km_manual": None, "km_manual_fecha": None}
    base.update(datos)
    return base


def registro(**datos):
    base = {"fecha": "2026-01-10", "km": 10000, "titulo": "Cambio de aceite y filtro", "categoria": "fluidos"}
    base.update(datos)
    return base


def por_clave(items):
    return {i["clave"]: i for i in items}


# ---------------------------------------------------------------- fechas

def test_sumar_meses_no_se_pasa_del_fin_de_mes():
    assert sumar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert sumar_meses(date(2024, 1, 31), 1) == date(2024, 2, 29)  # año bisiesto
    assert sumar_meses(date(2025, 12, 15), 12) == date(2026, 12, 15)
    assert sumar_meses(date(2026, 3, 31), -1) == date(2026, 2, 28)


def test_dias_por_km_normal_y_acotado():
    assert dias_por_km(10000, 1250) == round(10000 / 1250 * 30.44)
    assert dias_por_km(0, 1250) == 0
    # Un valor imposible (error de tipeo o copia vieja) se acota en vez de desbordar la suma de fechas.
    assert dias_por_km(10 ** 18, 1) == DIAS_MAX
    assert dias_por_km(-10 ** 18, 1) == -DIAS_MAX
    assert dias_por_km(1000, None) == DIAS_MAX


def test_estado_por_dias_y_por_km():
    assert estado(0) == "vencido"
    assert estado(-3) == "vencido"
    assert estado(90, -1) == "vencido"      # los km mandan aunque falte tiempo
    assert estado(40, 900) == "pronto"      # a menos de 1.000 km
    assert estado(10) == "pronto"
    assert estado(40, 5000) == "ok"


def test_vencimientos_avisa_antes_segun_el_tipo():
    docs = [
        {"tipo": "vtv", "vence": (HOY + timedelta(days=20)).isoformat(), "cada_meses": 12, "detalle": ""},
        {"tipo": "seguro_pago", "vence": (HOY + timedelta(days=20)).isoformat(), "cada_meses": 1, "detalle": ""},
        {"tipo": "registro", "vence": None, "cada_meses": None, "detalle": "clase B"},
        {"tipo": "patente", "vence": (HOY - timedelta(days=2)).isoformat(), "cada_meses": 2, "detalle": ""},
    ]
    salida = {v["doc"]["tipo"]: v for v in vencimientos(docs, HOY)}
    assert salida["vtv"]["estado"] == "pronto"        # avisa un mes antes
    assert salida["seguro_pago"]["estado"] == "ok"    # los pagos mensuales avisan a los 7 días
    assert salida["registro"]["estado"] == "sin_fecha" and salida["registro"]["dias"] is None
    assert salida["patente"]["estado"] == "vencido"
    assert salida["vtv"]["dias"] == 20


# ---------------------------------------------------------------- plan de mantenimiento

def test_plan_sin_perfil_de_uso_no_estima():
    assert plan_mantenimiento(vehiculo(), [registro()], HOY) == []


def test_plan_de_moto_no_usa_los_intervalos_de_auto():
    assert plan_mantenimiento(vehiculo(carroceria="moto", uso="promedio"), [registro()], HOY) == []


def test_plan_usa_los_km_que_le_pasan():
    """El mismo cálculo tiene que dar el mismo resultado en la ficha y en los recordatorios."""
    v = vehiculo(uso="promedio")
    con_pocos = por_clave(plan_mantenimiento(v, [registro()], HOY, km_hoy=12000))
    con_muchos = por_clave(plan_mantenimiento(v, [registro()], HOY, km_hoy=25000))
    assert con_pocos["aceite"]["faltan_km"] == 8000
    assert con_pocos["aceite"]["estado"] == "ok"
    assert con_muchos["aceite"]["faltan_km"] == -5000
    assert con_muchos["aceite"]["estado"] == "vencido"


def test_plan_con_km_absurdo_no_revienta():
    """Un kilometraje imposible ya guardado (copia vieja o error de tipeo) no puede tumbar la página."""
    v = vehiculo(uso="personalizado", km_mes=1, km_inicial=999_999_999_999, creado="2026-01-01")
    items = plan_mantenimiento(v, [registro()], HOY)
    estimados = [i for i in items if i["estado"] != "sin_dato"]
    assert estimados, "tiene que devolver los services estimados"
    for i in estimados:
        assert -DIAS_MAX <= i["dias"] <= DIAS_MAX
        assert i["estado"] in ("vencido", "pronto", "ok")
        assert 1900 <= int(i["fecha"][:4]) <= 2126


def test_plan_marca_sin_dato_cuando_no_hay_registro():
    items = por_clave(plan_mantenimiento(vehiculo(uso="poco"), [], HOY))
    assert items["aceite"]["estado"] == "sin_dato" and items["aceite"]["ultimo"] is None


# ---------------------------------------------------------------- kilometrajes

def test_km_por_mes():
    assert km_por_mes(vehiculo(uso="poco")) == 500
    assert km_por_mes(vehiculo(uso="personalizado", km_mes=2000)) == 2000
    assert km_por_mes(vehiculo(uso="personalizado", km_mes=0)) is None
    assert km_por_mes(vehiculo()) is None


def test_km_estimado_sin_perfil_es_el_ultimo_km_conocido():
    v = vehiculo(km_inicial=50000, creado="2020-01-01")
    assert km_estimado(v, [registro(km=52000)], HOY) == 52000   # sin uso, no se estima nada
    assert km_estimado(vehiculo(), []) == 0


def test_km_estimado_con_perfil_suma_lo_que_se_manejo():
    v = vehiculo(uso="promedio", km_inicial=10000, creado="2026-09-18")  # un mes antes de HOY
    assert km_estimado(v, [], HOY) == 10000 + round(1250 * 30 / 30.44)


def test_km_manual_manda_sobre_el_km_inicial():
    v = vehiculo(km_inicial=10000, creado="2026-01-01", km_manual=15000, km_manual_fecha="2026-09-01")
    assert km_estimado(v, [], HOY) == 15000


def test_promedio_medido_necesita_dos_lecturas_separadas():
    assert promedio_medido([registro(km=10000)]) is None
    dos = [registro(fecha="2026-01-01", km=10000), registro(fecha="2026-04-01", km=13000)]
    assert promedio_medido(dos) == round(3000 / (90 / 30.44))
    # Si el odómetro baja (carga desordenada) o pasan menos de dos meses, no se estima.
    assert promedio_medido([registro(fecha="2026-01-01", km=13000), registro(fecha="2026-04-01", km=10000)]) is None
    assert promedio_medido([registro(fecha="2026-01-01"), registro(fecha="2026-01-20")]) is None
