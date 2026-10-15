"""Da (o quita) el rango de administrador a una cuenta.

Uso, en la consola del servidor, dentro de la carpeta de la app:
    python3 tools/admin.py <usuario>            # lo hace administrador
    python3 tools/admin.py <usuario> --quitar   # se lo saca
"""
import os
import sqlite3
import sys

BASE = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bitacora.db"))

if len(sys.argv) < 2:
    sys.exit(__doc__)
quitar = "--quitar" in sys.argv[2:]
with sqlite3.connect(BASE) as db:
    columnas = {r[1] for r in db.execute("PRAGMA table_info(usuarios)")}
    if "admin" not in columnas:
        sys.exit("Primero abrí la página una vez con la versión nueva (crea la columna).")
    n = db.execute("UPDATE usuarios SET admin = ? WHERE usuario = ? COLLATE NOCASE", (0 if quitar else 1, sys.argv[1])).rowcount
print(("Listo: " + sys.argv[1] + (" ya no es administrador." if quitar else " ahora es administrador.")) if n
      else "No existe la cuenta " + sys.argv[1])
