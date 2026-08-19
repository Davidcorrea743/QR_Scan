import os
import uuid

from fastapi import HTTPException, UploadFile

import database

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}


def _extension(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in (".png", ".jpg", ".jpeg", ".webp") else ".png"


def guardar_imagen(upload: UploadFile, prefijo: str, normalizar: bool = True) -> str:
    if upload.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail="Formato de imagen no permitido. Usa PNG, JPG o WEBP.",
        )
    return guardar_imagen_bytes(upload.file.read(), upload.filename, prefijo, normalizar)


def guardar_imagen_bytes(
    datos: bytes, nombre_original: str, prefijo: str, normalizar: bool = True
) -> str:
    nombre = f"{prefijo}_{uuid.uuid4().hex}{_extension(nombre_original)}"
    ruta = os.path.join(database.UPLOADS_DIR, nombre)
    with open(ruta, "wb") as f:
        f.write(datos)
    if normalizar:
        _normalizar_foto(ruta)
    return nombre


def _normalizar_foto(ruta: str):
    try:
        from PIL import Image

        img = Image.open(ruta)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        w, h = img.size
        s = min(w, h)
        img = img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
        img = img.resize((600, 600), Image.LANCZOS)
        img.save(ruta, quality=90, optimize=True)
    except ImportError:
        pass


def eliminar_archivo(nombre: str):
    if not nombre:
        return
    ruta = os.path.join(database.UPLOADS_DIR, nombre)
    if os.path.exists(ruta):
        os.remove(ruta)
