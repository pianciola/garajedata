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
# Motos: alta/edición, fotos, bitácora, controles, exportación y aislamiento de cuenta.
r = c.post("/vehiculo/nuevo", data={"carroceria": "moto", "marca": "yamaha", "modelo": "Moto de prueba",
                                   "km_inicial": "5000", "calcular_uso": "1", "uso": "promedio"})
assert r.status_code == 302
vid_moto = int(r.location.rsplit("/", 1)[1])
with sqlite3.connect(os.environ["DB_PATH"]) as db:
    assert db.execute("SELECT carroceria,marca,uso FROM vehiculos WHERE id=?", (vid_moto,)).fetchone() == ("moto", "Yamaha", None)
assert c.post(f"/vehiculo/{vid_moto}/editar", data={"carroceria": "moto", "marca": "Yamaha", "modelo": "Moto editada", "color": "#c0262d"}).status_code == 302
assert c.post(f"/vehiculo/{vid_moto}/editar", data={"tipo_vehiculo": "moto", "carroceria": "sedan", "marca": "Yamaha", "modelo": "Moto editada", "cilindrada": "155"}).status_code == 302
with sqlite3.connect(os.environ["DB_PATH"]) as db:
    assert db.execute("SELECT carroceria,cilindrada FROM vehiculos WHERE id=?", (vid_moto,)).fetchone() == ("moto", 155)
for ruta in (f"/vehiculo/{vid_moto}", f"/vehiculo/{vid_moto}/libro"):
    assert "155 cc" in c.get(ruta).get_data(as_text=True)
html = c.get(f"/vehiculo/{vid_moto}/editar").get_data(as_text=True)
assert 'name="tipo_vehiculo" value="moto" checked' in html
assert 'id="opciones-auto" hidden' in html
assert 'name="cilindrada"' in html and 'value="155"' in html
from nucleo import datos_vehiculo_form
for valor in ("0", "-1", "10001", "nan", "abc", ""):
    with app.test_request_context(method="POST", data={"tipo_vehiculo": "moto", "cilindrada": valor}):
        assert datos_vehiculo_form()["cilindrada"] is None
with app.test_request_context(method="POST", data={"tipo_vehiculo": "auto", "carroceria": "moto", "cilindrada": "155"}):
    d = datos_vehiculo_form()
    assert d["carroceria"] == "sedan" and d["cilindrada"] is None
assert c.post(f"/vehiculo/{vid_moto}/registro/nuevo", data={"titulo": "Service según manual", "fecha": date.today().isoformat(), "prox_km": "7000"}).status_code == 302
assert c.post(f"/vehiculo/{vid_moto}/registro/nuevo", data={"modo": "pendiente", "titulo": "Revisar cadena", "pend_km": "6500"}).status_code == 302
for ruta in ("/", f"/vehiculo/{vid_moto}", f"/vehiculo/{vid_moto}/libro"):
    html = c.get(ruta).get_data(as_text=True)
    assert 'data-type="moto"' in html
assert "Service según manual" in c.get(f"/vehiculo/{vid_moto}").get_data(as_text=True)
assert c.post(f"/vehiculo/{vid_moto}/foto", data={"imagen_modo": "foto", "foto": (io.BytesIO(original), "moto.jpg")}).status_code == 302
assert 'car-photo' in c.get(f"/vehiculo/{vid_moto}").get_data(as_text=True)
with app.app_context():
    from nucleo import get_db
    from mantenimiento import plan_mantenimiento
    v = get_db().execute("SELECT * FROM vehiculos WHERE id=?", (vid_moto,)).fetchone()
    assert plan_mantenimiento(dict(v) | {"uso": "promedio"}, []) == []
exportado = c.get("/cuenta/exportar").data
importadora = app.test_client()
assert importadora.post("/registro", data={"usuario": "moto_importada", "clave": "prueba-123", "clave2": "prueba-123", "acepto": "1"}).status_code == 302
assert importadora.get(f"/vehiculo/{vid_moto}").status_code == 404
assert importadora.post("/cuenta/importar", data={"copia": (io.BytesIO(exportado), "copia.zip")}).status_code == 302
with sqlite3.connect(os.environ["DB_PATH"]) as db:
    assert db.execute("SELECT COUNT(*) FROM vehiculos WHERE carroceria='moto' AND modelo='Moto editada'").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM vehiculos WHERE carroceria='moto' AND cilindrada=155").fetchone()[0] == 2
from nucleo import patente_info
for patente, tipo, texto in (("a12 3bcd", "moto-mercosur", "A12\n3BCD"),
                              ("234 abc", "moto-vieja", "234\nABC")):
    assert patente_info(patente, "moto") == (tipo, texto)
    for carroceria in (None, "sedan", "hatchback", "pickup", "suv"):
        assert not patente_info(patente, carroceria)[0].startswith("moto-")
    with sqlite3.connect(os.environ["DB_PATH"]) as db:
        db.execute("UPDATE vehiculos SET patente=? WHERE id IN (1,?)", (patente, vid_moto))
    for ruta in ("/", f"/vehiculo/{vid_moto}", f"/vehiculo/{vid_moto}/libro"):
        html = c.get(ruta).get_data(as_text=True)
        assert f'plate-{tipo}' in html and texto in html
    for ruta in ("/vehiculo/1", "/vehiculo/1/libro"):
        assert 'class="plate plate-moto-' not in c.get(ruta).get_data(as_text=True)
assert patente_info("ABC123", "sedan") == ("vieja", "ABC 123")
assert patente_info("AB123CD", "sedan") == ("mercosur", "AB 123 CD")
from catalogo import MARCAS_MOTO, logo_marca, catalogo_js
for marca in MARCAS_MOTO:
    url = logo_marca(marca, "moto")
    assert url and c.get(url).status_code == 200, marca
    assert catalogo_js()["logosMoto"][marca]["logo"] == url
assert logo_marca("Honda", "moto").endswith("motos/honda.svg")
assert logo_marca("Honda", "sedan").endswith("marcas/honda.png")
with sqlite3.connect(os.environ["DB_PATH"]) as db:
    db.execute("UPDATE vehiculos SET marca='Honda' WHERE id IN (1,?)", (vid_moto,))
for ruta in ("/", "/registro/nuevo", f"/vehiculo/{vid_moto}", f"/vehiculo/{vid_moto}/libro"):
    assert "marcas/motos/honda.svg" in c.get(ruta).get_data(as_text=True)
assert "marcas/motos/honda.svg" not in c.get("/vehiculo/1").get_data(as_text=True)
print("REGRESIONES OK")
