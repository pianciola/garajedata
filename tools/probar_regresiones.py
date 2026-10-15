"""Reproduce los fallos de la auditoría sin tocar datos reales."""
import io
import json
import os
from pathlib import Path
import random
import re
import sqlite3
import sys
import tempfile
import zipfile
from datetime import date

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
temporal = Path(tempfile.mkdtemp(prefix="garajedata-regresiones-"))
os.environ.update(DB_PATH=str(temporal / "prueba.db"), UPLOAD_DIR=str(temporal / "uploads"),
                  RESPALDOS_DIR=str(temporal / "respaldos"), SECRET_KEY="solo-pruebas-temporales")
from app import app  # noqa: E402
from nucleo import init_db  # noqa: E402
import archivos  # noqa: E402
from PIL import Image  # noqa: E402
from tools.sanear_fotos import sanear  # noqa: E402

app.config.update(CSRF_APAGADO=True, TESTING=True)
c = app.test_client()
assert c.post("/registro", data={"usuario": "regresion", "clave": "anterior-123", "clave2": "anterior-123", "acepto": "1"}).status_code == 302
with c.session_transaction() as s:
    codigo = s["codigo_nuevo"]


def clonar(cliente):
    otro = app.test_client()
    otro.set_cookie("session", cliente.get_cookie("session").value)
    return otro


# Rotar contraseña cierra las sesiones anteriores, pero conserva la actual renovada.
anterior = clonar(c)
assert c.post("/cuenta", data={"actual": "anterior-123", "clave": "nueva-1234", "clave2": "nueva-1234"}).status_code == 302
assert anterior.get("/cuenta").status_code == 302
assert c.get("/cuenta").status_code == 200
anterior = clonar(c)
recuperada = app.test_client()
assert recuperada.post("/recuperar", data={"usuario": "regresion", "codigo": codigo, "clave": "recuperada-123", "clave2": "recuperada-123"}).status_code == 302
assert anterior.get("/cuenta").status_code == 302
c = recuperada
otra = app.test_client()
otra.post("/login", data={"usuario": "regresion", "clave": "recuperada-123"})
anterior = clonar(c)
c.post("/logout")
assert anterior.get("/cuenta").status_code == 302
assert otra.get("/cuenta").status_code == 200  # salir no cierra otros dispositivos
c = otra
legada = app.test_client()
with legada.session_transaction() as s:
    s["uid"] = 1
assert legada.get("/cuenta").status_code == 302
init_db(); init_db()
assert c.get("/cuenta").status_code == 200  # migración idempotente

c.post("/vehiculo/nuevo", data={"marca": "Ford", "modelo": "Focus", "km_inicial": "129499"})
c.post("/vehiculo/1/registro/nuevo", data={"titulo": "Aceite", "fecha": date.today().isoformat(), "km": "130000"})
c.post("/vehiculo/1/km", data={"km": "145000"})
html = c.get("/").get_data(as_text=True)
tarjeta = re.search(r'<dl class="mini-stats">(.*?)</dl>', html, re.S).group(1)
assert "145.000 km" in tarjeta and "130.000 km" not in tarjeta


def cantidades():
    with sqlite3.connect(os.environ["DB_PATH"]) as db:
        return tuple(db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                     for tabla in ("vehiculos", "registros", "archivos", "pendientes"))


def importar(datos):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("garajedata.json", json.dumps(datos))
    return c.post("/cuenta/importar", data={"copia": (io.BytesIO(buf.getvalue()), "copia.zip")}, follow_redirects=True)


for campo in ("registros", "documentos", "pendientes", "archivos"):
    for mal in (7, {}, "texto", [7]):
        antes = cantidades()
        r = importar({"vehiculos": [{"marca": "Ford"}, {campo: mal}]})
        assert r.status_code == 200 and "estructura" in r.get_data(as_text=True)
        assert cantidades() == antes  # ni el primer vehículo se importa parcialmente
for mal in ([], 7, {"vehiculos": {}}, {"vehiculos": [7]},
            {"vehiculos": [{"registros": [{"id": [], "titulo": "x"}]}]},
            {"vehiculos": [{"archivos": [{"registro_id": {}, "en_el_zip": "a.jpg"}]}]}):
    antes = cantidades()
    assert importar(mal).status_code == 200
    assert cantidades() == antes
antes = cantidades()
assert importar({"vehiculos": [{"marca": "Ford", "modelo": "Ka", "registros": [], "pendientes": None}]}).status_code == 200
assert cantidades()[0] == antes[0] + 1

for campo, fecha in (("fecha", "2099-01-01"), ("fecha", "fecha mala"), ("fecha", ""), ("prox_fecha", "0001-01-01")):
    antes = cantidades()
    datos = {"titulo": "Conservar este título", "fecha": date.today().isoformat(), "detalle": "Conservar detalle", campo: fecha}
    r = c.post("/vehiculo/1/registro/nuevo", data=datos)
    assert r.status_code == 200 and cantidades() == antes
    assert "Conservar este título" in r.get_data(as_text=True) and "Conservar detalle" in r.get_data(as_text=True)
with sqlite3.connect(os.environ["DB_PATH"]) as db:
    rid = db.execute("SELECT id FROM registros LIMIT 1").fetchone()[0]
r = c.post(f"/registro/{rid}/editar", data={"titulo": "No guardar", "fecha": "2099-01-01"})
assert r.status_code == 200
with sqlite3.connect(os.environ["DB_PATH"]) as db:
    assert db.execute("SELECT titulo FROM registros WHERE id=?", (rid,)).fetchone()[0] == "Aceite"

# Un JPEG ya pequeño no debe conservar EXIF aunque recomprimirlo lo haga más pesado.
imagen = Image.new("RGB", (150, 100))
rng = random.Random(12)
imagen.putdata([tuple(rng.randrange(256) for _ in range(3)) for _ in range(15000)])
exif = Image.Exif()
exif[270] = "DATOS SINTETICOS"
exif[274] = 6
exif[34853] = {1: "N", 2: (1.0, 2.0, 3.0), 3: "W", 4: (4.0, 5.0, 6.0)}
buf = io.BytesIO()
imagen.save(buf, "JPEG", quality=10, optimize=True, exif=exif)
original = buf.getvalue()
limpia, mime = archivos.achicar(original, "image/jpeg")
with Image.open(io.BytesIO(limpia)) as im:
    assert not im.getexif() and im.size == (100, 150) and mime == "image/jpeg"
Path(archivos.CARPETA).mkdir(exist_ok=True)
Path(archivos.ruta("vieja.jpg")).write_bytes(original)
with sqlite3.connect(os.environ["DB_PATH"]) as db:
    db.execute("INSERT INTO archivos (vehiculo_id,nombre,archivo,mime,bytes,creado) VALUES (1,'prueba.jpg','vieja.jpg','image/jpeg',?,?)",
               (len(original), date.today().isoformat()))
assert sanear() == 1
respaldo = temporal / "originales.zip"
assert sanear(True, respaldo) == 1
with zipfile.ZipFile(respaldo) as z:
    assert z.read("vieja.jpg") == original
assert sanear() == 0
with Image.open(archivos.ruta("vieja.jpg")) as im:
    assert not im.getexif() and im.size == (100, 150)
with sqlite3.connect(os.environ["DB_PATH"]) as db:
    assert db.execute("SELECT bytes FROM archivos WHERE archivo='vieja.jpg'").fetchone()[0] == Path(archivos.ruta("vieja.jpg")).stat().st_size
print("REGRESIONES OK")
