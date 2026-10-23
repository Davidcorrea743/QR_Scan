"""Copia de seguridad de la base de datos SQLite.

Usa la API de backup de SQLite (conexión.backup), que produce una copia
consistente aunque la aplicación esté escribiendo al mismo tiempo.

Uso:
    python respaldar.py                 # crea respaldos/qr_tracker_AAAAMMDD_HHMMSS.db
    python respaldar.py --destino /ruta/archivo.db
"""

import argparse
import os
import sqlite3
from datetime import datetime

import database

TABLAS = ("usuarios", "empleados", "scans")


def respaldar(destino=None):
    """Crea una copia de la BD y devuelve la ruta del archivo generado."""
    if destino is None:
        carpeta = os.path.join(database.BASE_DIR, "respaldos")
        os.makedirs(carpeta, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(carpeta, f"qr_tracker_{marca}.db")
        # Si ya existe un respaldo en este segundo, numeramos para no sobrescribir.
        base, ext = os.path.splitext(destino)
        n = 1
        while os.path.exists(destino):
            destino = f"{base}_{n}{ext}"
            n += 1
    else:
        os.makedirs(os.path.dirname(os.path.abspath(destino)) or ".", exist_ok=True)

    origen = sqlite3.connect(database.DB_PATH)
    try:
        copia = sqlite3.connect(destino)
        try:
            origen.backup(copia)
        finally:
            copia.close()
    finally:
        origen.close()
    return destino


def conteos(path):
    """Filas por tabla de un archivo de BD (para verificar un respaldo)."""
    conn = sqlite3.connect(path)
    try:
        return {
            tabla: conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            for tabla in TABLAS
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Respalda la base de datos SQLite")
    parser.add_argument("--destino", help="Ruta del archivo .db de destino")
    args = parser.parse_args()

    ruta = respaldar(args.destino)
    print(f"Respaldo creado: {ruta}")
    c = conteos(ruta)
    for tabla, n in c.items():
        print(f"  {tabla}: {n}")


if __name__ == "__main__":
    main()
