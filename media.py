import io
import os
import uuid

from fastapi import HTTPException, UploadFile

import database

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
MAX_TAMANO_IMAGEN = 8 * 1024 * 1024  # 8 MB


def _extension(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in (".png", ".jpg", ".jpeg", ".webp") else ".png"


def _ruta_segura(nombre: str) -> str:
    """Resuelve un nombre de archivo confinado a UPLOADS_DIR (anti path-traversal)."""
    base = os.path.abspath(database.UPLOADS_DIR)
    ruta = os.path.abspath(os.path.join(base, os.path.basename(nombre or "")))
    if os.path.dirname(ruta) != base:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida.")
    return ruta


def _validar_imagen(datos: bytes):
    """Verifica que los bytes sean una imagen real (no solo el Content-Type declarado)."""
    from PIL import Image

    try:
        Image.open(io.BytesIO(datos)).verify()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="El archivo no es una imagen válida.",
        )


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
    if len(datos) > MAX_TAMANO_IMAGEN:
        raise HTTPException(
            status_code=400,
            detail="La imagen supera el tamaño máximo (8 MB).",
        )
    _validar_imagen(datos)
    nombre = f"{prefijo}_{uuid.uuid4().hex}{_extension(nombre_original)}"
    ruta = _ruta_segura(nombre)
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
    try:
        ruta = _ruta_segura(nombre)
    except HTTPException:
        return
    if os.path.exists(ruta):
        os.remove(ruta)
