"""Archivos subidos: documentos de la bóveda y fotos/facturas de los registros.

Se guardan fuera de static/, con un nombre al azar, y solo se sirven por rutas
que controlan quién los puede ver. Solo se aceptan imágenes y PDF, reconocidos
por su contenido (no por la extensión). Las fotos se achican para no llenar
el disco: una foto de celular de 4 MB queda en ~300 KB.
"""
import io
import warnings
import os
import secrets

try:
    from PIL import Image, ImageOps
except ImportError:  # sin Pillow se guardan tal cual
    Image = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
MAX_BYTES = 10 * 1024 * 1024          # por archivo
CUPO_USUARIO = 100 * 1024 * 1024      # por cuenta
LADO_MAX = 1800                        # px del lado más largo de las fotos

BOVEDA = {
    "cedula": "Cédula verde / azul",
    "seguro": "Constancia de seguro",
    "vtv": "VTV / RTO vigente",
    "titulo": "Título del automotor",
    "otro": "Otro documento",
}


def tipo_de(datos):
    """(mime, extensión) según los primeros bytes, o None si no es imagen ni PDF."""
    if datos.startswith(b"%PDF-"):
        return "application/pdf", ".pdf"
    if datos.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


# Una foto de celular rara vez pasa de 50 MP; más que eso es una «bomba» (un PNG chico que al abrirse
# ocupa gigas). Pillow avisa al superar el límite y falla al doblarlo: acá fallan las dos cosas.
if Image is not None:
    Image.MAX_IMAGE_PIXELS = 50_000_000
    warnings.simplefilter("error", Image.DecompressionBombWarning)


def achicar(datos, mime):
    """Foto más liviana: gira según el EXIF, limita el tamaño y pasa a JPEG.
    De paso descarta los metadatos (ubicación GPS de la foto, etc.)."""
    if Image is None or mime == "application/pdf":
        return datos, mime
    try:
        img = Image.open(io.BytesIO(datos))
        img = ImageOps.exif_transpose(img)
        img.thumbnail((LADO_MAX, LADO_MAX))
        if img.mode not in ("RGB", "L"):
            fondo = Image.new("RGB", img.size, (255, 255, 255))
            fondo.paste(img, mask=img.convert("RGBA").split()[-1])
            img = fondo
        salida = io.BytesIO()
        img.save(salida, "JPEG", quality=82, optimize=True)
    except Exception:  # imagen dañada o rara: se rechaza
        raise ValueError("La imagen no se pudo leer.")
    nuevo = salida.getvalue()
    return (nuevo, "image/jpeg") if len(nuevo) < len(datos) or mime != "image/jpeg" else (datos, mime)


def guardar(archivo, usados, solo_imagen=False):
    """Valida y guarda un archivo subido. Devuelve (nombre_en_disco, mime, bytes, nombre_original).
    Lanza ValueError con un mensaje para el usuario si no se puede."""
    datos = archivo.read(MAX_BYTES + 1)
    nombre = os.path.basename((archivo.filename or "archivo").replace("\\", "/"))[:120] or "archivo"
    if not datos:
        raise ValueError(f"«{nombre}» está vacío.")
    if len(datos) > MAX_BYTES:
        raise ValueError(f"«{nombre}» pesa más de 10 MB.")
    tipo = tipo_de(datos)
    if tipo is None:
        raise ValueError(f"«{nombre}» no es una foto (JPG, PNG, WEBP) ni un PDF.")
    if solo_imagen and tipo[0] == "application/pdf":
        raise ValueError("La foto del auto tiene que ser una imagen (JPG, PNG o WEBP), no un PDF.")
    datos, mime = achicar(datos, tipo[0])
    if usados + len(datos) > CUPO_USUARIO:
        raise ValueError("Llegaste al límite de 100 MB de archivos de tu cuenta. Borrá alguno para subir más.")
    ext = ".jpg" if mime == "image/jpeg" else tipo[1]
    if mime == "image/jpeg" and not nombre.lower().endswith((".jpg", ".jpeg")):
        nombre = os.path.splitext(nombre)[0] + ".jpg"
    os.makedirs(CARPETA, exist_ok=True)
    en_disco = secrets.token_hex(16) + ext
    with open(os.path.join(CARPETA, en_disco), "wb") as f:
        f.write(datos)
    return en_disco, mime, len(datos), nombre


LADO_AVATAR = 320  # px de la foto de perfil (cuadrada)


def guardar_avatar(archivo):
    """Foto de perfil: solo imágenes; se recorta cuadrada al centro, se achica y se guarda en JPEG
    sin metadatos. Devuelve el nombre en disco. Lanza ValueError con un mensaje para el usuario."""
    datos = archivo.read(MAX_BYTES + 1)
    if not datos:
        raise ValueError("Elegí una foto.")
    if len(datos) > MAX_BYTES:
        raise ValueError("La foto pesa más de 10 MB.")
    tipo = tipo_de(datos)
    if tipo is None or tipo[0] == "application/pdf":
        raise ValueError("La foto de perfil tiene que ser una imagen JPG, PNG o WEBP.")
    if Image is None:
        raise ValueError("Ahora no se pueden procesar fotos. Probá más tarde.")
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(datos)))
        img = ImageOps.fit(img.convert("RGB"), (LADO_AVATAR, LADO_AVATAR), centering=(0.5, 0.4))
        salida = io.BytesIO()
        img.save(salida, "JPEG", quality=85, optimize=True)
    except Exception:
        raise ValueError("La imagen no se pudo leer.")
    os.makedirs(CARPETA, exist_ok=True)
    en_disco = "avatar_" + secrets.token_hex(16) + ".jpg"
    with open(os.path.join(CARPETA, en_disco), "wb") as f:
        f.write(salida.getvalue())
    return en_disco


def ruta(en_disco):
    return os.path.join(CARPETA, os.path.basename(en_disco))


def borrar(nombres):
    for n in nombres:
        try:
            os.remove(ruta(n))
        except OSError:
            pass
