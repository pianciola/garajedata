"""Archivos para buscadores: robots.txt y sitemap.xml (solo las páginas públicas)."""
from nucleo import *  # noqa: F401,F403

PAGINAS_SITEMAP = ("index", "registrarse", "login", "terminos", "privacidad", "creditos")


@app.route("/robots.txt")
def robots():
    texto = "\n".join([
        "User-agent: *",
        "Allow: /$",
        "Allow: /registro",
        "Allow: /login",
        "Allow: /terminos",
        "Allow: /privacidad",
        "Allow: /creditos",
        "Allow: /static/",
        # Todo lo demás es de una cuenta, links compartidos o calendarios: no se indexa.
        "Disallow: /",
        f"Sitemap: {url_absoluta('sitemap')}",
        "",
    ])
    return Response(texto, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    hoy = date.today().isoformat()
    urls = "".join(f"<url><loc>{url_absoluta(p)}</loc><lastmod>{hoy}</lastmod></url>" for p in PAGINAS_SITEMAP)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    return Response(xml, mimetype="application/xml")
