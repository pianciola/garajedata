"""Copia de seguridad de la base, a mano.

Uso:  python tools/respaldo.py
Guarda respaldos/bitacora-AAAA-MM-DD.db junto a la base y deja solo los últimos 14.
(La app ya hace una por día sola; esto sirve para forzarla antes de un cambio grande.)
"""
import os
import sys

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, RAIZ)
from respaldos import carpeta_de, hacer_respaldo  # noqa: E402

BASE = os.environ.get("DB_PATH", os.path.join(RAIZ, "bitacora.db"))

if __name__ == "__main__":
    if not os.path.exists(BASE):
        sys.exit(f"No existe la base: {BASE}")
    destino = hacer_respaldo(BASE)
    print(f"Respaldo: {destino}" if destino else f"Ya había respaldo de hoy en {carpeta_de(BASE)}")
