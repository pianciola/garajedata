"""Quita metadatos de JPEG ya guardados. Requiere --aplicar y --respaldo RUTA.zip.

Sin --aplicar solo informa cuántas fotos necesitan limpieza. No imprime nombres ni datos EXIF.
El respaldo queda fuera de la app para permitir recuperar los originales si hiciera falta.
"""
import argparse
import io
import os
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nucleo import app, get_db  # noqa: E402
import archivos  # noqa: E402


def sanear(aplicar=False, respaldo=None):
    if aplicar and not respaldo:
        raise ValueError("Indicá un respaldo para conservar los originales.")
    modificadas = 0
    with app.app_context():
        db = get_db()
        nombres = {r[0] for r in db.execute("SELECT archivo FROM archivos WHERE mime = 'image/jpeg'")}
        nombres.update(r[0] for r in db.execute("SELECT foto FROM usuarios WHERE foto IS NOT NULL"))
        pendientes = []
        for nombre in sorted(nombres):
            ruta = Path(archivos.ruta(nombre))
            with archivos.Image.open(ruta) as imagen:
                limpiar = bool(imagen.getexif()) or any(
                    k in imagen.info for k in ("comment", "xmp", "icc_profile", "XML:com.adobe.xmp"))
            if limpiar:
                pendientes.append((nombre, ruta))
        if not aplicar:
            return len(pendientes)
        # Cerrar el ZIP completa su índice antes de tocar cualquier original.
        with zipfile.ZipFile(respaldo, "x", zipfile.ZIP_DEFLATED) as destino:
            for _, ruta in pendientes:
                destino.write(ruta, ruta.name)
        with zipfile.ZipFile(respaldo) as originales:
            for nombre, ruta in pendientes:
                datos = originales.read(ruta.name)
                nuevos, _ = archivos.achicar(datos, "image/jpeg")
                fd, temporal = tempfile.mkstemp(dir=ruta.parent, prefix="sanear-")
                try:
                    with os.fdopen(fd, "wb") as f:
                        f.write(nuevos)
                    os.replace(temporal, ruta)
                finally:
                    if os.path.exists(temporal):
                        os.unlink(temporal)
                db.execute("UPDATE archivos SET bytes = ? WHERE archivo = ?", (len(nuevos), nombre))
                db.commit()
                modificadas += 1
    return modificadas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--respaldo")
    args = parser.parse_args()
    print("FOTOS_SANEADAS" if args.aplicar else "FOTOS_POR_SANEAR", sanear(args.aplicar, args.respaldo))
