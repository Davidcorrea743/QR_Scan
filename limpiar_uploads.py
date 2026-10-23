"""Detecta (y opcionalmente elimina) archivos huérfanos de uploads/.

Un archivo es huérfano si ninguna referencia en la BD apunta a él:
  - empleados.foto
  - cualquier valor de la tabla empresa (logo, fondo, carnet_fondo,
    trasera_fondo, trasera_logo, galeria JSON, etc.)

Uso:
    python limpiar_uploads.py            # dry-run: solo informa
    python limpiar_uploads.py --borrar   # elimina los huérfanos
    python limpiar_uploads.py --borrar --lista   # muestra también los nombres
"""

import argparse
import json
import os

import database

EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".webp")


def _nombres_de_valor(valor):
    """Extrae nombres de archivo de un valor de texto (soporta JSON de galeria)."""
    if not valor or not isinstance(valor, str):
        return []
    valor = valor.strip()
    if not valor:
        return []
    if valor.startswith("["):
        try:
            datos = json.loads(valor)
        except json.JSONDecodeError:
            datos = None
        if isinstance(datos, list):
            return [str(v) for v in datos if isinstance(v, str)]
    return [valor]


def nombres_referenciados(conn):
    """Nombres de archivo de imagen (basenames) que la BD sigue referenciando."""
    referenciados = set()

    def _agregar(valor):
        for nombre in _nombres_de_valor(valor):
            nombre = os.path.basename(nombre)
            if nombre.lower().endswith(EXT_IMAGEN):
                referenciados.add(nombre)

    for fila in conn.execute("SELECT foto FROM empleados"):
        _agregar(fila["foto"])

    empresa = conn.execute("SELECT * FROM empresa").fetchone()
    if empresa:
        for valor in empresa:
            _agregar(valor)

    return referenciados


def purgar_huerfanos(borrar=False):
    """Recorre uploads/ y clasifica archivos. Solo borra con borrar=True."""
    uploads = database.UPLOADS_DIR
    resultado = {"existentes": [], "referenciados": [], "huerfanos": [], "borrados": []}
    if not os.path.isdir(uploads):
        return resultado

    conn = database.get_connection()
    try:
        referenciados = nombres_referenciados(conn)
    finally:
        conn.close()

    existentes = sorted(
        n
        for n in os.listdir(uploads)
        if os.path.isfile(os.path.join(uploads, n)) and not n.startswith(".")
    )
    huerfanos = [n for n in existentes if n not in referenciados]

    resultado["existentes"] = existentes
    resultado["referenciados"] = [n for n in existentes if n in referenciados]
    resultado["huerfanos"] = huerfanos

    if borrar and huerfanos:
        base = os.path.abspath(uploads)
        for nombre in huerfanos:
            ruta = os.path.abspath(os.path.join(base, os.path.basename(nombre)))
            if os.path.dirname(ruta) != base:
                continue
            try:
                os.remove(ruta)
                resultado["borrados"].append(nombre)
            except OSError:
                pass

    return resultado


def main():
    parser = argparse.ArgumentParser(description="Limpia archivos huérfanos de uploads/")
    parser.add_argument(
        "--borrar",
        action="store_true",
        help="Elimina los archivos huérfanos (por defecto solo informa: dry-run)",
    )
    parser.add_argument(
        "--lista", action="store_true", help="Muestra también los nombres de los huérfanos"
    )
    args = parser.parse_args()

    r = purgar_huerfanos(borrar=args.borrar)

    print(f"Carpeta: {database.UPLOADS_DIR}")
    print(f"Archivos existentes:      {len(r['existentes'])}")
    print(f"Referenciados en la BD:   {len(r['referenciados'])}")
    if args.borrar:
        print(f"Huérfanos borrados:       {len(r['borrados'])}")
    else:
        print(f"Huérfanos (se borrarían): {len(r['huerfanos'])}")
        print("(dry-run: usa --borrar para eliminarlos)")

    if args.lista and r["huerfanos"]:
        for nombre in r["huerfanos"][:50]:
            print(f"  - {nombre}")
        if len(r["huerfanos"]) > 50:
            print(f"  ... y {len(r['huerfanos']) - 50} más")


if __name__ == "__main__":
    main()
