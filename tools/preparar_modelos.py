"""Prepara el "Generic passenger car pack" (Comrade1280, CC BY 4.0) para la app.

Uso:  python tools/preparar_modelos.py

1. Extrae static/models/generic_passenger_car_pack.zip en static/models/pack/.
2. Achica las texturas a 1024 px para que la página cargue rápido.
3. En la textura de carrocería de cada auto separa la pintura del resto
   (plásticos, parrilla, manijas): la pintura pasa a gris con su sombreado
   y se marca en el canal alfa, así el visor 3D la pinta del color elegido.
4. Escribe static/models/modelos.json.
"""
import json
import os
import zipfile

from PIL import Image

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "models")
ZIP = os.path.join(RAIZ, "generic_passenger_car_pack.zip")
PACK = os.path.join(RAIZ, "pack")
TEX = os.path.join(PACK, "textures")
TAM = 1024

CREDITO = '"Generic passenger car pack" de Comrade1280 (CC BY 4.0)'
URL = "https://sketchfab.com/3d-models/generic-passenger-car-pack-20f9af9b8a404d5cb022ac6fe87f21f5"

# carrocería -> (objeto en el modelo, material de carrocería, cómo detectar la pintura)
AUTOS = {
    "hatchback": ("Hatchback Body", "Body_1", "color"),
    "sedan": ("Sedan Body", "Body_5", "color"),
    "rural": ("Wagon Body", "Body_8", "color"),
    "coupe": ("Coupe Body", "Body_0", "color"),
    "suv": ("SUV Body", "Body_7", "gris"),
    "pickup": ("Pickup Body", "Body_4", "color"),
    "utilitario": ("minivan body", "Body_2", "color"),
}


def rampa(x, a, b):
    """0 por debajo de a, 1 por encima de b, lineal en el medio."""
    return min(1.0, max(0.0, (x - a) / (b - a)))


def mascara_pintura(px, modo):
    r, g, b = (c / 255 for c in px[:3])
    v = max(r, g, b)
    if modo == "gris":
        # Pintura gris muy oscura (puertas ~0.04, capot ~0.11) frente a plásticos casi negros.
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return rampa(lum, 0.024, 0.033) * (1 - rampa(lum, 0.2, 0.26)), lum
    s = 0 if v == 0 else (v - min(r, g, b)) / v
    return rampa(s, 0.18, 0.32) * rampa(v, 0.04, 0.09), v


def hacer_pintable(nombre, modo):
    ruta = os.path.join(TEX, f"{nombre}_baseColor.png")
    im = Image.open(ruta).convert("RGBA")
    datos = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
    medidas = [mascara_pintura(p, modo) for p in datos]
    brillos = sorted(v for m, v in medidas if m > 0.5)
    ref = brillos[int(len(brillos) * 0.9)] if brillos else 1
    salida = []
    for p, (m, v) in zip(datos, medidas):
        if m <= 0:
            salida.append((p[0], p[1], p[2], 0))
        else:
            # En la textura gris el sombreado es muy marcado: se suaviza.
            sombra = min(1.0, v / ref) ** (0.5 if modo == "gris" else 1)
            gris = round(sombra * 240)
            salida.append((gris, gris, gris, round(m * 255)))
    im.putdata(salida)
    im.save(ruta, optimize=True)
    print(f"  {nombre}: pintura en {sum(1 for m, _ in medidas if m > 0.5) / len(medidas):.0%} de la textura")


def main():
    print("Extrayendo pack...")
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(PACK)

    print(f"Achicando texturas a {TAM} px...")
    for f in os.listdir(TEX):
        ruta = os.path.join(TEX, f)
        im = Image.open(ruta)
        if max(im.size) > TAM:
            im = im.resize((TAM, TAM * im.size[1] // im.size[0]), Image.LANCZOS)
            im.save(ruta, optimize=True, **({"quality": 88} if f.endswith(".jpeg") else {}))

    print("Separando la pintura...")
    for _, (_, material, modo) in AUTOS.items():
        hacer_pintable(material, modo)

    config = {
        tipo: {"archivo": "pack/scene.gltf", "nodo": nodo, "pintura": [material], "mascara": True,
               "credito": CREDITO, "url": URL}
        for tipo, (nodo, material, _) in AUTOS.items()
    }
    with open(os.path.join(RAIZ, "modelos.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("Listo: static/models/modelos.json actualizado.")


if __name__ == "__main__":
    main()
