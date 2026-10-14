"""Catálogo de marcas (con logo) y sus modelos más conocidos, con su carrocería."""
import unicodedata

# Logos: car-logos-dataset (copiados a static/img/marcas). Nombre de la marca -> slug del logo.
# (copias locales en static/img/marcas, para no depender de un servicio externo)
LOGO_URL = "/static/img/marcas/{}.png"
MARCAS = {
    "Alfa Romeo": "alfa-romeo", "Audi": "audi", "BMW": "bmw", "BYD": "byd",
    "Chery": "chery", "Chevrolet": "chevrolet", "Chrysler": "chrysler",
    "Citroën": "citroen", "Cupra": "cupra", "Dodge": "dodge", "DS": "ds",
    "Ferrari": "ferrari", "Fiat": "fiat", "Ford": "ford", "Geely": "geely",
    "Great Wall": "great-wall", "Haval": "haval", "Honda": "honda",
    "Hyundai": "hyundai", "Iveco": "iveco", "JAC": "jac", "Jaguar": "jaguar",
    "Jeep": "jeep", "Jetour": "jetour", "Kia": "kia", "Lamborghini": "lamborghini",
    "Land Rover": "land-rover", "Lexus": "lexus", "Maserati": "maserati",
    "Mazda": "mazda", "Mercedes-Benz": "mercedes-benz", "MG": "mg", "Mini": "mini",
    "Mitsubishi": "mitsubishi", "Nissan": "nissan", "Peugeot": "peugeot",
    "Porsche": "porsche", "RAM": "ram", "Renault": "renault", "Seat": "seat",
    "Skoda": "skoda", "Subaru": "subaru", "Suzuki": "suzuki", "Tesla": "tesla",
    "Toyota": "toyota", "Volkswagen": "volkswagen", "Volvo": "volvo",
}

# Logos mayormente negros/oscuros: en modo oscuro se invierten para que se vean.
LOGOS_OSCUROS = {
    "audi", "byd", "cupra", "jaguar", "kia", "lamborghini", "maserati",
    "mitsubishi", "nissan", "suzuki", "tesla", "toyota", "volkswagen",
}

# Modelos más conocidos de cada marca, agrupados por carrocería.
MODELOS = {
    "Alfa Romeo": {"hatchback": ["147", "Giulietta", "MiTo"], "sedan": ["156", "159", "Giulia"],
                   "suv": ["Stelvio", "Tonale", "Junior"]},
    "Audi": {"hatchback": ["A1", "A3 Sportback"], "sedan": ["A3 Sedán", "A4", "A6", "A8"],
             "rural": ["A4 Avant", "A6 Avant"], "coupe": ["A5", "TT", "R8"],
             "suv": ["Q2", "Q3", "Q5", "Q7", "Q8", "e-tron"]},
    "BMW": {"hatchback": ["Serie 1", "i3"], "sedan": ["Serie 3", "Serie 5", "Serie 7", "M3", "M5"],
            "coupe": ["Serie 2 Coupé", "Serie 4", "M4", "Z4"],
            "suv": ["X1", "X2", "X3", "X4", "X5", "X6", "X7", "iX"]},
    "BYD": {"hatchback": ["Dolphin", "Dolphin Mini"], "sedan": ["Seal", "Han", "King"],
            "suv": ["Yuan Plus", "Atto 3", "Song Plus", "Song Pro", "Tang"], "pickup": ["Shark"]},
    "Chery": {"hatchback": ["QQ"], "sedan": ["Arrizo 5"],
              "suv": ["Tiggo 2", "Tiggo 3", "Tiggo 4", "Tiggo 7", "Tiggo 8"]},
    "Chevrolet": {"hatchback": ["Onix", "Corsa", "Celta", "Agile", "Cruze 5", "Sonic"],
                  "sedan": ["Onix Plus", "Prisma", "Classic", "Cruze", "Astra", "Vectra"],
                  "rural": ["Spin", "Zafira", "Meriva"], "coupe": ["Camaro", "Corvette"],
                  "suv": ["Tracker", "Equinox", "Trailblazer", "Captiva"],
                  "pickup": ["S10", "Montana", "Silverado"]},
    "Chrysler": {"hatchback": ["PT Cruiser"], "sedan": ["300C"], "utilitario": ["Town & Country", "Pacifica"]},
    "Citroën": {"hatchback": ["C3", "C4", "C4 Cactus"], "sedan": ["C4 Lounge", "C-Elysée"],
                "rural": ["Xsara Picasso", "C4 Picasso"],
                "suv": ["C3 Aircross", "C4 Aircross", "C5 Aircross", "Basalt"],
                "utilitario": ["Berlingo", "Jumpy", "Jumper"]},
    "Cupra": {"hatchback": ["Born", "León"], "suv": ["Formentor", "Ateca", "Terramar"]},
    "Dodge": {"sedan": ["Charger", "Neon"], "coupe": ["Challenger", "Viper"], "suv": ["Journey", "Durango"]},
    "DS": {"hatchback": ["DS 3", "DS 4"], "sedan": ["DS 9"], "suv": ["DS 3 Crossback", "DS 7"]},
    "Ferrari": {"coupe": ["296 GTB", "F8 Tributo", "Roma", "SF90", "812 Superfast"], "suv": ["Purosangue"]},
    "Fiat": {"hatchback": ["Argo", "Mobi", "Palio", "Uno", "Punto", "500"],
             "sedan": ["Cronos", "Siena", "Grand Siena", "Linea"], "rural": ["Palio Weekend", "Idea"],
             "suv": ["Pulse", "Fastback", "600"], "pickup": ["Toro", "Strada", "Titano"],
             "utilitario": ["Fiorino", "Doblò", "Ducato"]},
    "Ford": {"hatchback": ["Ka", "Fiesta", "Focus", "Escort"], "sedan": ["Ka+", "Fiesta Sedán", "Focus Sedán", "Mondeo", "Falcon"],
             "coupe": ["Mustang"], "suv": ["EcoSport", "Territory", "Kuga", "Bronco Sport", "Bronco", "Explorer"],
             "pickup": ["Ranger", "Maverick", "F-100", "F-150"], "utilitario": ["Transit"]},
    "Geely": {"hatchback": ["Geometry C"], "sedan": ["Emgrand"], "suv": ["Coolray", "Okavango", "Tugella"]},
    "Great Wall": {"pickup": ["Poer", "Wingle 5", "Wingle 7"]},
    "Haval": {"suv": ["H6", "Jolion", "H2", "Dargo"]},
    "Honda": {"hatchback": ["Fit"], "sedan": ["City", "Civic", "Accord"], "suv": ["WR-V", "HR-V", "ZR-V", "CR-V"]},
    "Hyundai": {"hatchback": ["i10", "i20", "i30", "HB20"], "sedan": ["Accent", "Elantra", "Sonata"],
                "coupe": ["Veloster"], "suv": ["Creta", "Kona", "Tucson", "Santa Fe"], "utilitario": ["H-1"]},
    "Iveco": {"utilitario": ["Daily"]},
    "JAC": {"hatchback": ["E-JS1"], "suv": ["S2", "S3", "JS4"], "pickup": ["T6", "T8"]},
    "Jaguar": {"sedan": ["XE", "XF"], "coupe": ["F-Type"], "suv": ["E-Pace", "F-Pace", "I-Pace"]},
    "Jeep": {"suv": ["Renegade", "Compass", "Commander", "Cherokee", "Grand Cherokee", "Wrangler"],
             "pickup": ["Gladiator"]},
    "Jetour": {"suv": ["X70", "Dashing", "T2"]},
    "Kia": {"hatchback": ["Picanto", "Rio", "Soul"], "sedan": ["Rio Sedán", "Cerato", "K5"],
            "suv": ["Stonic", "Seltos", "Sportage", "Sorento"], "utilitario": ["Carnival"]},
    "Lamborghini": {"coupe": ["Huracán", "Aventador", "Revuelto"], "suv": ["Urus"]},
    "Land Rover": {"suv": ["Defender", "Discovery", "Discovery Sport", "Range Rover", "Range Rover Sport",
                           "Range Rover Evoque", "Range Rover Velar"]},
    "Lexus": {"sedan": ["IS", "ES", "LS"], "coupe": ["RC"], "suv": ["UX", "NX", "RX", "LX"]},
    "Maserati": {"sedan": ["Ghibli", "Quattroporte"], "coupe": ["MC20", "GranTurismo"], "suv": ["Grecale", "Levante"]},
    "Mazda": {"hatchback": ["Mazda2", "Mazda3"], "sedan": ["Mazda3 Sedán", "Mazda6"], "coupe": ["MX-5", "RX-8"],
              "suv": ["CX-3", "CX-30", "CX-5", "CX-9"], "pickup": ["BT-50"]},
    "Mercedes-Benz": {"hatchback": ["Clase A"], "sedan": ["Clase C", "Clase E", "Clase S", "CLA"],
                      "coupe": ["AMG GT", "SLK"], "suv": ["GLA", "GLB", "GLC", "GLE", "Clase G"],
                      "utilitario": ["Vito", "Sprinter"]},
    "MG": {"hatchback": ["MG3", "MG4"], "sedan": ["MG5"], "suv": ["ZS", "HS"]},
    "Mini": {"hatchback": ["Cooper", "Cooper 5 puertas"], "rural": ["Clubman"], "coupe": ["Cabrio"],
             "suv": ["Countryman"]},
    "Mitsubishi": {"sedan": ["Lancer"], "suv": ["ASX", "Eclipse Cross", "Outlander", "Montero", "Pajero"],
                   "pickup": ["L200"]},
    "Nissan": {"hatchback": ["March", "Note", "Tiida", "Leaf"], "sedan": ["Versa", "Sentra"], "coupe": ["Z", "370Z"],
               "suv": ["Kicks", "X-Trail", "Pathfinder"], "pickup": ["Frontier"]},
    "Peugeot": {"hatchback": ["206", "207", "208", "306", "307", "308"], "sedan": ["405", "408", "504", "508"],
                "suv": ["2008", "3008", "5008"], "pickup": ["Landtrek"],
                "utilitario": ["Partner", "Expert", "Boxer"]},
    "Porsche": {"coupe": ["911", "718 Cayman", "718 Boxster"], "sedan": ["Panamera", "Taycan"],
                "suv": ["Macan", "Cayenne"]},
    "RAM": {"pickup": ["700", "1000", "1500", "2500", "Rampage"]},
    "Renault": {"hatchback": ["Clio", "Sandero", "Sandero Stepway", "Kwid", "Twingo", "Mégane"],
                "sedan": ["Logan", "Symbol", "Fluence", "Renault 12", "Renault 9"],
                "suv": ["Duster", "Captur", "Kardian", "Koleos", "Arkana"],
                "pickup": ["Oroch", "Alaskan"], "utilitario": ["Kangoo", "Trafic", "Master"]},
    "Seat": {"hatchback": ["Ibiza", "León"], "sedan": ["Toledo"], "suv": ["Arona", "Ateca", "Tarraco"]},
    "Skoda": {"hatchback": ["Fabia"], "sedan": ["Octavia", "Superb"], "rural": ["Octavia Combi"],
              "suv": ["Kamiq", "Karoq", "Kodiaq"]},
    "Subaru": {"hatchback": ["Impreza"], "sedan": ["WRX", "Legacy"], "rural": ["Outback"], "coupe": ["BRZ"],
               "suv": ["XV / Crosstrek", "Forester"]},
    "Suzuki": {"hatchback": ["Swift", "Baleno", "Celerio", "Fun"], "suv": ["Jimny", "Vitara", "Grand Vitara", "S-Cross"]},
    "Tesla": {"sedan": ["Model 3", "Model S"], "suv": ["Model Y", "Model X"], "pickup": ["Cybertruck"]},
    "Toyota": {"hatchback": ["Etios", "Yaris", "Prius"], "sedan": ["Etios Sedán", "Yaris Sedán", "Corolla", "Camry"],
               "coupe": ["GR86", "Supra"], "suv": ["Corolla Cross", "C-HR", "RAV4", "SW4", "Land Cruiser"],
               "pickup": ["Hilux", "Tacoma"], "utilitario": ["Hiace"]},
    "Volkswagen": {"hatchback": ["Gol", "Gol Trend", "Fox", "Up!", "Polo", "Golf"],
                   "sedan": ["Voyage", "Virtus", "Vento", "Bora", "Passat"], "rural": ["Suran", "Vento Variant"],
                   "coupe": ["Scirocco", "Escarabajo"], "suv": ["Nivus", "T-Cross", "Taos", "Tiguan", "Touareg"],
                   "pickup": ["Saveiro", "Amarok"], "utilitario": ["Transporter", "Sharan", "Crafter"]},
    "Volvo": {"sedan": ["S60", "S90"], "rural": ["V60"], "suv": ["EX30", "XC40", "C40", "XC60", "XC90"]},
}


# Versiones / generaciones de los modelos más comunes. Varios modelos que
# comparten generaciones se escriben juntos separados por "|".
VERSIONES = {
    "Audi": {"A3 Sportback|A3 Sedán": ["8L", "8P", "8V", "8Y"], "A4|A4 Avant": ["B5", "B6", "B7", "B8", "B9"]},
    "BMW": {"Serie 1": ["E87", "F20", "F40"], "Serie 3|M3": ["E30", "E36", "E46", "E90", "F30", "G20"],
            "Serie 5|M5": ["E34", "E39", "E60", "F10", "G30"]},
    "Chevrolet": {"Corsa": ["Corsa B (Classic)", "Corsa C (Corsa II)"], "Onix|Onix Plus": ["1ª gen.", "2ª gen."],
                  "Cruze|Cruze 5": ["J300 (1ª gen.)", "J400 (2ª gen.)"], "S10": ["1ª gen.", "2ª gen.", "3ª gen."],
                  "Camaro": ["5ª gen.", "6ª gen."], "Tracker": ["1ª gen.", "2ª gen.", "3ª gen."]},
    "Citroën": {"C4|C4 Lounge": ["1ª gen.", "2ª gen.", "3ª gen."], "C3": ["1ª gen.", "2ª gen.", "3ª gen."]},
    "Fiat": {"Uno": ["Uno (1ª gen.)", "Novo Uno (2ª gen.)"], "Palio|Siena|Palio Weekend": ["Fase 1", "Fase 2", "Fase 3", "Fase 4"],
             "500": ["1ª gen.", "2ª gen."]},
    "Ford": {"Focus|Focus Sedán": ["MK1", "MK2", "MK3", "MK4"], "Fiesta|Fiesta Sedán": ["MK4", "MK5 (Max)", "MK6 (Kinetic)", "MK7"],
             "Ka": ["1ª gen.", "2ª gen.", "3ª gen."], "EcoSport": ["1ª gen.", "2ª gen. (Kinetic)"],
             "Ranger": ["1ª gen.", "2ª gen. (T6)", "3ª gen."], "Mustang": ["S197 (5ª gen.)", "S550 (6ª gen.)", "S650 (7ª gen.)"],
             "Mondeo": ["MK1", "MK2", "MK3", "MK4", "MK5"], "Escort": ["MK5", "MK6"]},
    "Honda": {"Civic": ["7ª gen.", "8ª gen.", "9ª gen.", "10ª gen.", "11ª gen."], "Fit": ["1ª gen.", "2ª gen.", "3ª gen."],
              "CR-V": ["2ª gen.", "3ª gen.", "4ª gen.", "5ª gen.", "6ª gen."]},
    "Hyundai": {"Tucson": ["JM (1ª gen.)", "LM (2ª gen.)", "TL (3ª gen.)", "NX4 (4ª gen.)"]},
    "Jeep": {"Wrangler": ["YJ", "TJ", "JK", "JL"], "Grand Cherokee": ["ZJ", "WJ", "WK", "WK2", "WL"]},
    "Mazda": {"MX-5": ["NA", "NB", "NC", "ND"], "Mazda3|Mazda3 Sedán": ["BK (1ª gen.)", "BL (2ª gen.)", "BM (3ª gen.)", "BP (4ª gen.)"]},
    "Mercedes-Benz": {"Clase C": ["W202", "W203", "W204", "W205", "W206"], "Clase E": ["W210", "W211", "W212", "W213", "W214"],
                      "Sprinter": ["1ª gen.", "2ª gen.", "3ª gen."]},
    "Mini": {"Cooper|Cooper 5 puertas": ["R50", "R56", "F56"]},
    "Nissan": {"Frontier": ["D22", "D40", "D23 (NP300)"]},
    "Peugeot": {"208": ["1ª gen.", "2ª gen."], "308": ["1ª gen.", "2ª gen.", "3ª gen."], "2008": ["1ª gen.", "2ª gen."],
                "3008": ["1ª gen.", "2ª gen."], "Partner": ["1ª gen.", "2ª gen."]},
    "Porsche": {"911": ["964", "993", "996", "997", "991", "992"]},
    "Renault": {"Clio": ["Clio I", "Clio II", "Clio III", "Clio IV", "Clio V"], "Mégane": ["Mégane I", "Mégane II", "Mégane III", "Mégane IV"],
                "Sandero|Sandero Stepway|Logan": ["1ª gen.", "2ª gen."], "Duster": ["1ª gen.", "2ª gen."],
                "Kangoo": ["1ª gen.", "2ª gen.", "3ª gen."]},
    "Toyota": {"Hilux": ["6ª gen.", "7ª gen.", "8ª gen."], "SW4": ["1ª gen.", "2ª gen.", "3ª gen."],
               "Corolla": ["E110", "E120", "E140", "E170", "E210"], "RAV4": ["XA20", "XA30", "XA40", "XA50"],
               "Etios|Etios Sedán": ["Fase 1", "Fase 2"]},
    "Volkswagen": {"Gol": ["G1", "G2 (Gol bola)", "G3", "G4"], "Gol Trend|Voyage": ["G5", "G6", "G7"],
                   "Golf": ["MK1", "MK2", "MK3", "MK4", "MK5", "MK6", "MK7", "MK8"], "Polo": ["Polo Classic", "MK4", "MK6"],
                   "Vento": ["A5", "A6", "A7"], "Amarok": ["1ª gen.", "Restyling (V6)", "2ª gen."],
                   "Suran": ["Fase 1", "Fase 2"], "Fox": ["Fase 1", "Fase 2", "Fase 3"]},
}
# Siempre se ofrecen, además de las específicas del modelo.
VERSIONES_GENERICAS = ["Pre-restyling (fase 1)", "Restyling (fase 2)"]


def _norm(texto):
    """Minúsculas, sin acentos ni espacios repetidos: "  Citroën " -> "citroen"."""
    sin_acentos = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sin_acentos.lower().split())


_SLUGS = {_norm(k): v for k, v in MARCAS.items()}
_MARCAS = {_norm(k): k for k in MARCAS}


def canon_marca(marca):
    """Devuelve la marca como figura en el catálogo ("ford" -> "Ford"), o tal cual si no está."""
    return _MARCAS.get(_norm(marca), (marca or "").strip())


def canon_modelo(marca, modelo):
    """Igual que canon_marca pero para el modelo, dentro de su marca."""
    for lista in MODELOS.get(marca, {}).values():
        for m in lista:
            if _norm(m) == _norm(modelo):
                return m
    return (modelo or "").strip()


def logo_marca(marca):
    slug = _SLUGS.get(_norm(marca))
    return LOGO_URL.format(slug) if slug else None


def logo_oscuro(marca):
    return _SLUGS.get(_norm(marca)) in LOGOS_OSCUROS


def catalogo_js():
    """Datos para el formulario: {marca: {logo, oscuro, modelos: [[modelo, carrocería], ...],
    versiones: {modelo: [...]}}} y las versiones genéricas."""
    datos = {}
    for marca, slug in MARCAS.items():
        modelos = sorted(((m, tipo) for tipo, lista in MODELOS.get(marca, {}).items() for m in lista),
                         key=lambda x: x[0].lower())
        versiones = {m: v for clave, v in VERSIONES.get(marca, {}).items() for m in clave.split("|")}
        datos[marca] = {"logo": LOGO_URL.format(slug), "oscuro": slug in LOGOS_OSCUROS,
                        "modelos": [list(x) for x in modelos], "versiones": versiones}
    return {"marcas": datos, "versionesGenericas": VERSIONES_GENERICAS}
