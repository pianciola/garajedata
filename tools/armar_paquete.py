"""Arma el paquete para subir a PythonAnywhere.

Uso:  python tools/armar_paquete.py USUARIO [--sin-base]

Genera en para_subir/:
  garajedata.zip                      la app (con bitacora.db salvo --sin-base)
  USUARIO_pythonanywhere_com_wsgi.py  configuración WSGI, sin claves adentro

--sin-base sirve para actualizar el código sin pisar los datos cargados online.
"""
import os
import sys
import zipfile

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SALIDA = os.path.join(RAIZ, "para_subir")
# El pack original queda solo en la PC: la página usa los .glb separados de models/tipos/.
EXCLUIR = ("generic_passenger_car_pack.zip", "__pycache__", ".pyc", os.path.join("models", "pack"),
           "_swtest")

WSGI = '''# GarajeData - configuración WSGI para PythonAnywhere.
# No contiene claves: la clave de sesiones se genera en el servidor.
import os
import secrets
import sys

proyecto = "/home/{usuario}/garajedata"
if proyecto not in sys.path:
    sys.path.insert(0, proyecto)


def leer(nombre):
    try:
        with open(os.path.join(proyecto, nombre), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


# Clave para firmar las sesiones: se genera una sola vez en el servidor.
clave = leer(".secret_key")
if not clave:
    clave = secrets.token_hex(32)
    with open(os.path.join(proyecto, ".secret_key"), "w", encoding="utf-8") as f:
        f.write(clave)
os.environ["SECRET_KEY"] = clave
os.environ["GARAJEDATA_HTTPS"] = "1"  # cookie Secure y HSTS: el sitio publicado siempre va por HTTPS

from app import app as application  # noqa: E402
'''


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    usuario = sys.argv[1]
    con_base = "--sin-base" not in sys.argv
    os.makedirs(SALIDA, exist_ok=True)

    incluir = ["app.py", "nucleo.py", "respaldos.py", "legal.py", "consejos.py", "rutas", os.path.join("tools", "respaldo.py"), os.path.join("tools", "sanear_fotos.py"), "catalogo.py", "mantenimiento.py", "archivos.py", "requirements.txt",
               "templates", "static"]
    if con_base:
        incluir.append("bitacora.db")
    destino = os.path.join(SALIDA, "garajedata.zip")
    n = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for item in incluir:
            origen = os.path.join(RAIZ, item)
            rutas = [origen] if os.path.isfile(origen) else [
                os.path.join(r, f) for r, _, fs in os.walk(origen) for f in fs]
            for ruta in rutas:
                if any(x in ruta for x in EXCLUIR):
                    continue
                z.write(ruta, os.path.relpath(ruta, RAIZ).replace(os.sep, "/"))
                n += 1

    wsgi = os.path.join(SALIDA, f"{usuario}_pythonanywhere_com_wsgi.py")
    with open(wsgi, "w", encoding="utf-8") as f:
        f.write(WSGI.format(usuario=usuario))
    print(f"{destino}: {n} archivos, {os.path.getsize(destino) / 1e6:.1f} MB "
          f"({'con' if con_base else 'sin'} base de datos)")
    print(wsgi)


if __name__ == "__main__":
    main()
