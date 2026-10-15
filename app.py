"""GarajeData — bitácora del automotor.

App Flask + SQLite para llevar el registro de controles, cambios de fluidos,
piezas, reparaciones y modificaciones de uno o más vehículos.

nucleo.py tiene la app y lo común; cada archivo de rutas/ suma sus páginas.
"""
from nucleo import app  # noqa: F401
from rutas import (admin, agenda, boveda, cuentas, datos, estadisticas, importar, legal, libro,  # noqa: F401,E402
                   registros, sitio, transferir, vehiculos)

if __name__ == "__main__":
    app.run(debug=True)
