"""Separa el pack de autos en un .glb liviano por carrocería.

Uso:  python tools/separar_modelos.py      (después de tools/preparar_modelos.py)

El pack trae los 9 autos en un solo archivo (~11 MB entre geometría y
texturas): cualquier página tenía que bajar todo para mostrar un auto. Este
script arma static/models/tipos/<carroceria>.glb con solo ese auto, sus ruedas
y sus texturas pasadas a WebP (la pintura conserva la máscara en el alfa), y
actualiza modelos.json para usarlos.
"""
import io
import json
import os
import struct

from PIL import Image

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "models")
PACK = os.path.join(RAIZ, "pack")
SALIDA = os.path.join(RAIZ, "tipos")
CALIDAD = 82
LADO_MAX = 1024

COMPONENTES = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
CANTIDAD = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# ---------------------------------------------------------------- matrices 4x4 (column-major, como glTF)

def mult(a, b):
    return [sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]


def matriz_nodo(n):
    if "matrix" in n:
        return n["matrix"]
    tx, ty, tz = n.get("translation", (0, 0, 0))
    x, y, z, w = n.get("rotation", (0, 0, 0, 1))
    sx, sy, sz = n.get("scale", (1, 1, 1))
    r = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
         2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
         2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
         0, 0, 0, 1]
    for i in range(3):
        r[i] *= sx
        r[4 + i] *= sy
        r[8 + i] *= sz
    r[12], r[13], r[14] = tx, ty, tz
    return r


def aplicar(m, p):
    x, y, z = p
    return [m[0] * x + m[4] * y + m[8] * z + m[12],
            m[1] * x + m[5] * y + m[9] * z + m[13],
            m[2] * x + m[6] * y + m[10] * z + m[14]]


# ---------------------------------------------------------------- lectura del pack

class Pack:
    def __init__(self):
        with open(os.path.join(PACK, "scene.gltf"), encoding="utf-8") as f:
            self.g = json.load(f)
        with open(os.path.join(PACK, self.g["buffers"][0]["uri"]), "rb") as f:
            self.bin = f.read()
        self.padre = {}
        for i, n in enumerate(self.g["nodes"]):
            for h in n.get("children", []):
                self.padre[h] = i
        self.mundo = {}

    def nodo(self, nombre):
        for i, n in enumerate(self.g["nodes"]):
            if n.get("name") == nombre:
                return i
        raise SystemExit(f"No existe el objeto «{nombre}» en el pack")

    def matriz_mundo(self, i):
        if i not in self.mundo:
            m = matriz_nodo(self.g["nodes"][i])
            self.mundo[i] = mult(self.matriz_mundo(self.padre[i]), m) if i in self.padre else m
        return self.mundo[i]

    def subarbol(self, i):
        yield i
        for h in self.g["nodes"][i].get("children", []):
            yield from self.subarbol(h)

    def caja(self, i):
        """Caja en coordenadas del mundo de todo lo que cuelga del nodo."""
        mn, mx = [float("inf")] * 3, [float("-inf")] * 3
        for j in self.subarbol(i):
            n = self.g["nodes"][j]
            if "mesh" not in n:
                continue
            m = self.matriz_mundo(j)
            for p in self.g["meshes"][n["mesh"]]["primitives"]:
                a = self.g["accessors"][p["attributes"]["POSITION"]]
                for esquina in [(x, y, z) for x in (a["min"][0], a["max"][0])
                                for y in (a["min"][1], a["max"][1]) for z in (a["min"][2], a["max"][2])]:
                    q = aplicar(m, esquina)
                    mn = [min(u, v) for u, v in zip(mn, q)]
                    mx = [max(u, v) for u, v in zip(mx, q)]
        return mn, mx

    def con_ruedas(self, carroceria):
        """La carrocería y los objetos del mismo nivel cuyo centro cae dentro
        de ella (en el pack las ruedas no cuelgan de la carrocería)."""
        mn, mx = self.caja(carroceria)
        elegidos = [carroceria]
        for h in self.g["nodes"][self.padre[carroceria]].get("children", []):
            if h == carroceria or "body" in self.g["nodes"][h].get("name", "").lower():
                continue
            cmn, cmx = self.caja(h)
            if cmn[0] == float("inf"):
                continue
            centro = [(a + b) / 2 for a, b in zip(cmn, cmx)]
            if all(mn[k] <= centro[k] <= mx[k] for k in range(3)):
                elegidos.append(h)
        return elegidos

    def datos_accessor(self, i):
        """Bytes del accessor, sin intercalar (byteStride justo)."""
        a = self.g["accessors"][i]
        bv = self.g["bufferViews"][a["bufferView"]]
        tam_elem = struct.calcsize("<" + COMPONENTES[a["componentType"]]) * CANTIDAD[a["type"]]
        paso = bv.get("byteStride", tam_elem)
        inicio = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        if paso == tam_elem:
            return self.bin[inicio:inicio + tam_elem * a["count"]]
        return b"".join(self.bin[inicio + k * paso:inicio + k * paso + tam_elem] for k in range(a["count"]))


# ---------------------------------------------------------------- escritura de un .glb por tipo

class Glb:
    def __init__(self):
        self.g = {"asset": {"version": "2.0", "generator": "GarajeData separar_modelos.py"},
                  "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "materials": [],
                  "textures": [], "images": [], "samplers": [], "accessors": [], "bufferViews": [],
                  "buffers": [{"byteLength": 0}],
                  "extensionsUsed": ["EXT_texture_webp"], "extensionsRequired": ["EXT_texture_webp"]}
        self.bin = bytearray()
        self.mapas = {"mesh": {}, "material": {}, "texture": {}, "image": {}, "sampler": {}, "accessor": {}}

    def vista(self, datos, target=None):
        while len(self.bin) % 4:
            self.bin += b"\0"
        bv = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(datos)}
        if target:
            bv["target"] = target
        self.bin += datos
        self.g["bufferViews"].append(bv)
        return len(self.g["bufferViews"]) - 1

    def agregar(self, tipo, i, crear):
        if i not in self.mapas[tipo]:
            self.mapas[tipo][i] = crear()
        return self.mapas[tipo][i]

    def accessor(self, pack, i, target):
        def crear():
            a = {k: v for k, v in pack.g["accessors"][i].items() if k not in ("bufferView", "byteOffset")}
            a["bufferView"] = self.vista(pack.datos_accessor(i), target)
            self.g["accessors"].append(a)
            return len(self.g["accessors"]) - 1
        return self.agregar("accessor", i, crear)

    def imagen(self, pack, i):
        def crear():
            ruta = os.path.join(PACK, pack.g["images"][i]["uri"])
            img = Image.open(ruta)
            img.thumbnail((LADO_MAX, LADO_MAX))
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.mode else "RGB")
            # Si el alfa es todo opaco no hace falta guardarlo.
            if img.mode == "RGBA" and img.getchannel("A").getextrema() == (255, 255):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, "WEBP", quality=CALIDAD, method=6, alpha_quality=100)
            self.g["images"].append({"bufferView": self.vista(buf.getvalue()), "mimeType": "image/webp"})
            return len(self.g["images"]) - 1
        return self.agregar("image", i, crear)

    def textura(self, pack, i):
        def crear():
            t = pack.g["textures"][i]
            nueva = {"extensions": {"EXT_texture_webp": {"source": self.imagen(pack, t["source"])}}}
            if "sampler" in t:
                nueva["sampler"] = self.agregar("sampler", t["sampler"], lambda: (
                    self.g["samplers"].append(pack.g["samplers"][t["sampler"]]), len(self.g["samplers"]) - 1)[1])
            self.g["textures"].append(nueva)
            return len(self.g["textures"]) - 1
        return self.agregar("texture", i, crear)

    def material(self, pack, i):
        def remapear(x):
            if isinstance(x, dict):
                return {k: (self.textura(pack, v) if k == "index" else remapear(v)) for k, v in x.items()}
            if isinstance(x, list):
                return [remapear(v) for v in x]
            return x

        def crear():
            self.g["materials"].append(remapear(pack.g["materials"][i]))
            return len(self.g["materials"]) - 1
        return self.agregar("material", i, crear)

    def malla(self, pack, i):
        def crear():
            m = pack.g["meshes"][i]
            prims = []
            for p in m["primitives"]:
                q = {k: v for k, v in p.items() if k not in ("attributes", "indices", "material")}
                q["attributes"] = {k: self.accessor(pack, a, 34962) for k, a in p["attributes"].items()}
                if "indices" in p:
                    q["indices"] = self.accessor(pack, p["indices"], 34963)
                if "material" in p:
                    q["material"] = self.material(pack, p["material"])
                prims.append(q)
            self.g["meshes"].append({**{k: v for k, v in m.items() if k != "primitives"}, "primitives": prims})
            return len(self.g["meshes"]) - 1
        return self.agregar("mesh", i, crear)

    def nodo(self, pack, i, matriz=None):
        n = pack.g["nodes"][i]
        nuevo = {k: v for k, v in n.items() if k in ("name",)}
        nuevo["matrix"] = matriz or matriz_nodo(n)
        if "mesh" in n:
            nuevo["mesh"] = self.malla(pack, n["mesh"])
        self.g["nodes"].append(nuevo)
        idx = len(self.g["nodes"]) - 1
        hijos = [self.nodo(pack, h) for h in n.get("children", [])]
        if hijos:
            self.g["nodes"][idx]["children"] = hijos
        return idx

    def guardar(self, ruta):
        for k in ("samplers", "textures", "images"):
            if not self.g[k]:
                del self.g[k]
        while len(self.bin) % 4:
            self.bin += b"\0"
        self.g["buffers"][0]["byteLength"] = len(self.bin)
        js = json.dumps(self.g, separators=(",", ":")).encode()
        js += b" " * (-len(js) % 4)
        with open(ruta, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(self.bin)))
            f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
            f.write(struct.pack("<II", len(self.bin), 0x004E4942) + bytes(self.bin))


def main():
    with open(os.path.join(RAIZ, "modelos.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    pack = Pack()
    os.makedirs(SALIDA, exist_ok=True)
    total = 0
    for tipo, c in cfg.items():
        nodo = c.get("nodo_pack") or c.get("nodo")
        if not nodo:
            continue
        glb = Glb()
        raiz = {"name": tipo, "children": []}
        glb.g["nodes"].append(raiz)
        glb.g["scenes"][0]["nodes"] = [0]
        # Cada pieza queda con su posición final en el mundo, como en el pack.
        for i in pack.con_ruedas(pack.nodo(nodo)):
            raiz["children"].append(glb.nodo(pack, i, pack.matriz_mundo(i)))
        ruta = os.path.join(SALIDA, f"{tipo}.glb")
        glb.guardar(ruta)
        peso = os.path.getsize(ruta)
        total += peso
        print(f"{tipo:11} {peso / 1e6:5.2f} MB  ({len(raiz['children']) - 1} ruedas/piezas)")
        c.update(archivo=f"tipos/{tipo}.glb", nodo_pack=nodo)
        c.pop("nodo", None)
    with open(os.path.join(RAIZ, "modelos.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"Total {total / 1e6:.2f} MB (antes: el pack entero en cada página)")


if __name__ == "__main__":
    main()
