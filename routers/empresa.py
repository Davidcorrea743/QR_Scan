import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

import database
import media
from auth import require_admin

router = APIRouter(prefix="/empresa", tags=["empresa"])


@router.get("")
def obtener(user=Depends(require_admin)):
    conn = database.get_connection()
    try:
        row = conn.execute("SELECT * FROM empresa WHERE id = 1").fetchone()
    finally:
        conn.close()
    return dict(row) if row else {}


@router.put("")
def actualizar(
    nombre: str = Form(None),
    redes: str = Form(None),
    logo: UploadFile = File(None),
    fondo: UploadFile = File(None),
    carnet_fondo: UploadFile = File(None),
    user=Depends(require_admin),
):
    conn = database.get_connection()
    try:
        existing = conn.execute("SELECT * FROM empresa WHERE id = 1").fetchone()
        valores = {}
        if nombre is not None:
            valores["nombre"] = nombre.strip()
        if redes is not None:
            try:
                parsed = json.loads(redes)
                assert isinstance(parsed, list)
            except (json.JSONDecodeError, AssertionError):
                raise HTTPException(status_code=400, detail="redes debe ser una lista JSON")
            valores["redes"] = json.dumps(parsed, ensure_ascii=False)

        if logo:
            nuevo_logo = media.guardar_imagen(logo, "logo", normalizar=False)
            valores["logo"] = nuevo_logo
        if fondo:
            nuevo_fondo = media.guardar_imagen(fondo, "fondo", normalizar=False)
            valores["fondo"] = nuevo_fondo
        if carnet_fondo:
            nuevo_carnet_fondo = media.guardar_imagen(carnet_fondo, "carnet_fondo", normalizar=False)
            valores["carnet_fondo"] = nuevo_carnet_fondo

        if not valores:
            raise HTTPException(status_code=400, detail="Sin datos para actualizar")

        if existing:
            sets = ", ".join(f"{k} = ?" for k in valores)
            conn.execute(f"UPDATE empresa SET {sets} WHERE id = 1", (*valores.values(),))
        else:
            cols = ", ".join(valores)
            placeholders = ", ".join("?" for _ in valores)
            conn.execute(
                f"INSERT INTO empresa (id, {cols}) VALUES (1, {placeholders})",
                (*valores.values(),),
            )
        conn.commit()

        if logo and existing and existing["logo"] and existing["logo"] != nuevo_logo:
            media.eliminar_archivo(existing["logo"])
        if fondo and existing and existing["fondo"] and existing["fondo"] != nuevo_fondo:
            media.eliminar_archivo(existing["fondo"])
        if carnet_fondo and existing and existing["carnet_fondo"] and existing["carnet_fondo"] != nuevo_carnet_fondo:
            media.eliminar_archivo(existing["carnet_fondo"])
    finally:
        conn.close()
    return {"ok": True}
