"""Términos y condiciones y política de privacidad (el texto está en legal.py)."""
from markupsafe import Markup, escape

import legal
from nucleo import *  # noqa: F401,F403


def con_negritas(texto):
    """Escapa el texto y convierte **así** en <b>así</b>."""
    return Markup(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", str(escape(texto))))


app.jinja_env.filters["negritas"] = con_negritas


def pagina_legal(clave):
    return render_template("legal.html", doc=legal.PAGINAS[clave], clave=clave,
                           actualizacion=legal.ACTUALIZACION)


@app.route("/terminos")
def terminos():
    return pagina_legal("terminos")


@app.route("/privacidad")
def privacidad():
    return pagina_legal("privacidad")
