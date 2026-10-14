"""Corre la prueba completa de páginas (tools/probar_paginas.py) dentro de pytest."""
import os
import subprocess
import sys

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def test_todas_las_paginas():
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "tools", "probar_paginas.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0 and "TODO OK" in r.stdout, r.stdout + r.stderr


def test_respaldo(tmp_path):
    import sqlite3
    base = tmp_path / "b.db"
    with sqlite3.connect(base) as db:
        db.execute("CREATE TABLE t (x)")
        db.execute("INSERT INTO t VALUES (1)")
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "tools", "respaldo.py")], capture_output=True, text=True,
                       env={**os.environ, "DB_PATH": str(base), "RESPALDOS_DIR": str(tmp_path / "r")})
    assert r.returncode == 0, r.stderr
    copias = list((tmp_path / "r").glob("bitacora-*.db"))
    assert not list((tmp_path / "r").glob("*.tmp"))
    assert len(copias) == 1
    with sqlite3.connect(copias[0]) as db:
        assert db.execute("SELECT x FROM t").fetchone() == (1,)


def test_respaldo_guarda_14(tmp_path):
    import sqlite3
    import sys as _s
    from datetime import date, timedelta
    _s.path.insert(0, RAIZ)
    from respaldos import hacer_respaldo
    base = tmp_path / "b.db"
    sqlite3.connect(base).close()
    for i in range(20):
        hacer_respaldo(str(base), str(tmp_path / "r"), date(2026, 1, 1) + timedelta(days=i))
    copias = sorted(p.name for p in (tmp_path / "r").glob("bitacora-*.db"))
    assert len(copias) == 14 and copias[-1] == "bitacora-2026-01-20.db"
    assert hacer_respaldo(str(base), str(tmp_path / "r"), date(2026, 1, 20)) is None
