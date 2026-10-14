"""Copias de seguridad de la base: una por día, se guardan las últimas 14.

La app hace la del día sola con la primera visita (el plan gratis de PythonAnywhere no tiene
tareas programadas). También se puede correr a mano: python tools/respaldo.py
"""
import glob
import os
import sqlite3
from datetime import date

GUARDAR = 14


def carpeta_de(base):
    return os.environ.get("RESPALDOS_DIR", os.path.join(os.path.dirname(os.path.abspath(base)), "respaldos"))


def hacer_respaldo(base, carpeta=None, dia=None):
    """Copia en caliente (sirve con la página funcionando). Devuelve la ruta, o None si ya existía."""
    carpeta = carpeta or carpeta_de(base)
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, f"bitacora-{(dia or date.today()).isoformat()}.db")
    if os.path.exists(destino):
        return None
    origen, copia = sqlite3.connect(base), sqlite3.connect(destino + ".tmp")
    try:
        with copia:
            origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    os.replace(destino + ".tmp", destino)
    for viejo in sorted(glob.glob(os.path.join(carpeta, "bitacora-*.db")))[:-GUARDAR]:
        os.remove(viejo)
    return destino
