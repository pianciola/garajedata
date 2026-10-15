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

# Tema de cada marca para las páginas de sus vehículos: (color de acento, origen, año de fundación).
# El color es el que se asocia a la marca, ajustado para que se lea bien sobre el fondo oscuro.
TEMAS = {
    "Alfa Romeo": ("#d0202e", "italiana", 1910), "Audi": ("#c8102e", "alemana", 1909),
    "BMW": ("#1c69d4", "alemana", 1916), "BYD": ("#2b7de9", "china", 1995),
    "Chery": ("#d71920", "china", 1997), "Chevrolet": ("#d4a12a", "estadounidense", 1911),
    "Chrysler": ("#3f72b0", "estadounidense", 1925), "Citroën": ("#da291c", "francesa", 1919),
    "Cupra": ("#c27a4a", "española", 2018), "Dodge": ("#d81e1e", "estadounidense", 1900),
    "DS": ("#a58b63", "francesa", None), "Ferrari": ("#ef1c24", "italiana", 1947),
    "Fiat": ("#c41230", "italiana", 1899), "Ford": ("#2f74e0", "estadounidense", 1903),
    "Geely": ("#2c6fd6", "china", 1986), "Great Wall": ("#c8102e", "china", 1984),
    "Haval": ("#e2231a", "china", 2013), "Honda": ("#e40521", "japonesa", 1948),
    "Hyundai": ("#3a7bd5", "surcoreana", 1967), "Iveco": ("#2c6bd1", "italiana", 1975),
    "JAC": ("#e4002b", "china", 1964), "Jaguar": ("#2e8b57", "británica", 1922),
    "Jeep": ("#7a8f3a", "estadounidense", 1941), "Jetour": ("#0aa5a5", "china", 2018),
    "Kia": ("#d6213b", "surcoreana", 1944), "Lamborghini": ("#d9a520", "italiana", 1963),
    "Land Rover": ("#2a8a52", "británica", 1948), "Lexus": ("#a7adb5", "japonesa", 1989),
    "Maserati": ("#3563b0", "italiana", 1914), "Mazda": ("#c1272d", "japonesa", 1920),
    "Mercedes-Benz": ("#a9b2bd", "alemana", 1926), "MG": ("#d3122a", "de origen británico", 1924),
    "Mini": ("#2b7a4f", "británica", 1959), "Mitsubishi": ("#e60012", "japonesa", 1970),
    "Nissan": ("#c3002f", "japonesa", 1933), "Peugeot": ("#2f5fbf", "francesa", 1810),
    "Porsche": ("#c9a227", "alemana", 1931), "RAM": ("#c8102e", "estadounidense", 2010),
    "Renault": ("#f2c200", "francesa", 1899), "Seat": ("#d24a1e", "española", 1950),
    "Skoda": ("#4ba82e", "checa", 1895), "Subaru": ("#2f63c4", "japonesa", 1953),
    "Suzuki": ("#e30613", "japonesa", 1909), "Tesla": ("#e82127", "estadounidense", 2003),
    "Toyota": ("#eb0a1e", "japonesa", 1937), "Volkswagen": ("#2b6cc4", "alemana", 1937),
    "Volvo": ("#3a6ea5", "sueca", 1927),
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
# Versiones de equipamiento que se vendieron en Argentina (sugerencias: el campo acepta cualquier texto).
# Abarcan varias generaciones; los modelos que comparten versiones van juntos separados por "|".
EQUIPAMIENTOS = {
    "Chevrolet": {"Cruze|Cruze 5": ["LS", "LT", "LTZ", "LTZ+", "Premier", "RS"],
                  "Onix|Onix Plus": ["Joy", "LS", "LT", "LTZ", "Premier", "RS"],
                  "Prisma": ["Joy", "LS", "LT", "LTZ"], "Agile": ["LS", "LT", "LTZ"], "Sonic": ["LS", "LT", "LTZ"],
                  "Corsa|Classic": ["GL", "GLS", "Wind", "Spirit", "LS", "LT"],
                  "S10": ["LS", "LT", "LTZ", "High Country", "Z71"], "Tracker": ["LS", "LT", "LTZ", "Premier", "RS"],
                  "Spin": ["LS", "LT", "LTZ", "Activ", "Premier"], "Meriva": ["GL", "GLS", "GL Plus"]},
    "Ford": {"Focus|Focus Sedán": ["Ambiente", "Trend", "Ghia", "Exe", "Titanium", "SE", "SE Plus", "ST"],
             "Fiesta|Fiesta Sedán": ["Ambiente", "Edge", "Trend", "Titanium", "S", "SE", "ST"],
             "Ka|Ka+": ["Fly", "Viral", "Tattoo", "S", "SE", "SEL", "Freestyle"],
             "EcoSport": ["XL", "XLS", "XLT", "Freestyle", "Titanium", "Storm", "SE"],
             "Ranger": ["XL", "XLS", "XLT", "Limited", "Wildtrak", "Raptor"],
             "Territory": ["Trend", "SEL", "Titanium"], "Kuga": ["SE", "Titanium"]},
    "Volkswagen": {"Gol": ["Power", "Dub", "Country", "Trendline", "Comfortline", "Highline"],
                   "Gol Trend|Voyage": ["Trendline", "Comfortline", "Highline", "Pacific", "Sportline"],
                   "Golf": ["Trendline", "Comfortline", "Highline", "GTI", "R"],
                   "Polo": ["Trendline", "Comfortline", "Highline", "Track", "GTS"],
                   "Vento": ["Advance", "Luxury", "Sportline", "Comfortline", "Highline", "GLI"],
                   "Virtus": ["Trendline", "Comfortline", "Highline", "Exclusive", "GTS"],
                   "T-Cross": ["Trendline", "Comfortline", "Highline", "Hero"], "Taos": ["Comfortline", "Highline", "Hero"],
                   "Nivus": ["Comfortline", "Highline", "Hero"],
                   "Amarok": ["Startline", "Trendline", "Comfortline", "Highline", "Extreme", "Black Style"],
                   "Suran": ["Trendline", "Comfortline", "Highline", "Track", "Cross"],
                   "Fox": ["Trendline", "Comfortline", "Highline", "Sportline", "Route"],
                   "Up!": ["Take", "Move", "High", "Cross"], "Saveiro": ["Power", "Trendline", "Highline", "Cross"]},
    "Toyota": {"Corolla": ["XLi", "XEi", "SEG", "GR-Sport", "HV"], "Corolla Cross": ["XLi", "XEi", "SEG", "GR-Sport"],
               "Etios|Etios Sedán": ["X", "XS", "XLS", "Platinum"], "Yaris|Yaris Sedán": ["XS", "XLS", "S"],
               "Hilux": ["DX", "SR", "SRV", "SRX", "GR-Sport", "Conquest"],
               "SW4": ["SR", "SRV", "SRX", "Diamond", "GR-Sport"], "RAV4": ["TX", "VX", "Limited"]},
    "Fiat": {"Palio|Siena|Palio Weekend": ["Fire", "EL", "ELX", "HLX", "Attractive", "Essence", "Adventure"],
             "Cronos": ["Drive", "Like", "Precision", "S-Design"], "Argo": ["Drive", "Precision", "HGT", "Trekking"],
             "Uno": ["Fire", "Way", "Attractive", "Sporting", "Evo"], "Mobi": ["Easy", "Like", "Way", "Trekking"],
             "Toro": ["Freedom", "Volcano", "Ultra", "Ranch"],
             "Strada": ["Working", "Adventure", "Endurance", "Freedom", "Volcano", "Ranch"],
             "500": ["Pop", "Lounge", "Cult", "Abarth"], "Pulse": ["Drive", "Audace", "Impetus", "Abarth"]},
    "Peugeot": {"206": ["XR", "XS", "XT", "GTI"], "207": ["XR", "XS", "XT", "GTi"],
                "208": ["Like", "Active", "Allure", "Feline", "GT", "GTi"], "2008": ["Active", "Allure", "Feline", "GT", "Sport"],
                "308": ["Active", "Allure", "Feline", "GT"], "408": ["Allure", "Feline", "Sport"],
                "3008": ["Active", "Allure", "Feline", "GT"]},
    "Renault": {"Clio": ["Authentique", "Expression", "Privilège", "Mío", "Dynamique"],
                "Sandero|Logan": ["Authentique", "Expression", "Pack", "Privilège", "Life", "Zen", "Intens"],
                "Sandero Stepway": ["Expression", "Privilège", "Zen", "Intens"],
                "Duster": ["Expression", "Dynamique", "Privilège", "Zen", "Intens", "Iconic"],
                "Kangoo": ["Authentique", "Confort", "Zen", "Stepway"], "Kwid": ["Life", "Zen", "Intens", "Outsider", "Iconic"],
                "Mégane": ["Expression", "Dynamique", "Privilège", "Luxe", "GT", "RS"],
                "Fluence": ["Expression", "Dynamique", "Privilège", "Luxe", "GT"], "Captur": ["Life", "Zen", "Intens"]},
    "Honda": {"Civic": ["LX", "EX", "EXL", "EXS", "Si", "Type R"], "Fit": ["LX", "EX", "EXL"], "City": ["LX", "EX", "EXL"],
              "HR-V": ["LX", "EX", "EXL", "Touring"], "CR-V": ["LX", "EX", "EXL"]},
    "Nissan": {"March": ["Active", "Sense", "Advance", "SR"], "Versa": ["Sense", "Advance", "Exclusive", "SR"],
               "Sentra": ["Sense", "Advance", "Exclusive", "SR"], "Kicks": ["Sense", "Advance", "Exclusive", "SR"],
               "Frontier": ["S", "SE", "XE", "LE", "Pro-4X", "Platinum"]},
    "Jeep": {"Renegade": ["Sport", "Longitude", "Limited", "Trailhawk", "Serie S"],
             "Compass": ["Sport", "Longitude", "Limited", "Trailhawk", "Serie S"]},
    "Citroën": {"C3": ["Live", "Feel", "Shine", "Exclusive"], "C4|C4 Lounge": ["Tendance", "Exclusive", "Live", "Feel", "Shine"],
                "C4 Cactus": ["Live", "Feel", "Shine", "Noir"]},
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


def tema_marca(marca):
    """Colores y datos de la marca para «vestir» las páginas de ese vehículo; None si no está en el catálogo."""
    marca = _MARCAS.get(_norm(marca))
    if marca not in TEMAS:
        return None
    color, origen, anio = TEMAS[marca]
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))

    def lineal(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    luz = 0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b)
    claro = [round(c + (255 - c) * 0.18) for c in (r, g, b)]
    texto = "#0e1014" if luz > 0.3 else "#fff"  # sobre colores claros (dorado, plata, amarillo) va texto oscuro
    estilo = (f"--accent: {color}; --accent-hover: #{claro[0]:02x}{claro[1]:02x}{claro[2]:02x}; "
              f"--accent-rgb: {r} {g} {b}; --accent-soft: rgb({r} {g} {b} / .12); --on-accent: {texto};")
    logo = logo_marca(marca)
    return {"marca": marca, "color": color, "estilo": estilo, "logo": logo, "logo_oscuro": logo_oscuro(marca),
            "origen": f"Marca {origen}" + (f" · fundada en {anio}" if anio else "")}


def equipamientos_de(marca, modelo):
    """Versiones de equipamiento conocidas de un modelo (para sugerirlas y para ordenar datos viejos)."""
    for clave, lista in EQUIPAMIENTOS.get(canon_marca(marca), {}).items():
        if _norm(modelo) in (_norm(m) for m in clave.split("|")):
            return lista
    return []


def catalogo_js():
    """Datos para el formulario: {marca: {logo, oscuro, modelos: [[modelo, carrocería], ...],
    versiones: {modelo: [...]}}} y las versiones genéricas."""
    datos = {}
    for marca, slug in MARCAS.items():
        modelos = sorted(((m, tipo) for tipo, lista in MODELOS.get(marca, {}).items() for m in lista),
                         key=lambda x: x[0].lower())
        versiones = {m: v for clave, v in VERSIONES.get(marca, {}).items() for m in clave.split("|")}
        equipamientos = {m: v for clave, v in EQUIPAMIENTOS.get(marca, {}).items() for m in clave.split("|")}
        datos[marca] = {"logo": LOGO_URL.format(slug), "oscuro": slug in LOGOS_OSCUROS,
                        "modelos": [list(x) for x in modelos], "versiones": versiones, "equipamientos": equipamientos}
    return {"marcas": datos, "versionesGenericas": VERSIONES_GENERICAS}
