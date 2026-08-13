import json
from typing import List

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
    if not row:
        return {}
    data = dict(row)
    try:
        data["galeria"] = json.loads(data["galeria"]) if data.get("galeria") else []
    except (json.JSONDecodeError, TypeError):
        data["galeria"] = []
    return data


@router.delete("/imagen/{campo}")
def eliminar_imagen(campo: str, user=Depends(require_admin)):
    CAMPOS_VALIDOS = {"titulo", "logo", "fondo", "carnet_fondo", "trasera_fondo", "trasera_logo"}
    if campo not in CAMPOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Campo de imagen no válido")
    conn = database.get_connection()
    try:
        existing = conn.execute("SELECT * FROM empresa WHERE id = 1").fetchone()
        if existing and existing[campo]:
            media.eliminar_archivo(existing[campo])
            conn.execute(f"UPDATE empresa SET {campo} = NULL WHERE id = 1")
            conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.delete("/galeria/{nombre}")
def eliminar_imagen_galeria(nombre: str, user=Depends(require_admin)):
    conn = database.get_connection()
    try:
        existing = conn.execute("SELECT * FROM empresa WHERE id = 1").fetchone()
        if not existing or not existing["galeria"]:
            return {"ok": True}
        try:
            galeria = json.loads(existing["galeria"])
        except (json.JSONDecodeError, TypeError):
            galeria = []
        if nombre in galeria:
            galeria.remove(nombre)
            media.eliminar_archivo(nombre)
            conn.execute(
                "UPDATE empresa SET galeria = ? WHERE id = 1",
                (json.dumps(galeria) if galeria else None,),
            )
            conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.put("")
def actualizar(
    nombre: str = Form(None),
    redes: str = Form(None),
    ubicacion: str = Form(None),
    titulo: UploadFile = File(None),
    logo: UploadFile = File(None),
    fondo: UploadFile = File(None),
    carnet_fondo: UploadFile = File(None),
    trasera_fondo: UploadFile = File(None),
    trasera_logo: UploadFile = File(None),
    trasera_mensaje: str = Form(None),
    trasera_correo: str = Form(None),
    trasera_telefono: str = Form(None),
    galeria: List[UploadFile] = File(None),
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
        if ubicacion is not None:
            valores["ubicacion"] = ubicacion.strip()
        if trasera_mensaje is not None:
            valores["trasera_mensaje"] = trasera_mensaje.strip()
        if trasera_correo is not None:
            valores["trasera_correo"] = trasera_correo.strip()
        if trasera_telefono is not None:
            valores["trasera_telefono"] = trasera_telefono.strip()

        if galeria:
            try:
                actual = json.loads(existing["galeria"]) if existing and existing["galeria"] else []
            except (json.JSONDecodeError, TypeError):
                actual = []
            for upload in galeria:
                if upload and upload.filename:
                    nuevo = media.guardar_imagen(upload, "galeria", normalizar=False)
                    actual.append(nuevo)
            valores["galeria"] = json.dumps(actual)

        if titulo:
            nuevo_titulo = media.guardar_imagen(titulo, "titulo", normalizar=False)
            valores["titulo"] = nuevo_titulo
        if logo:
            nuevo_logo = media.guardar_imagen(logo, "logo", normalizar=False)
            valores["logo"] = nuevo_logo
        if fondo:
            nuevo_fondo = media.guardar_imagen(fondo, "fondo", normalizar=False)
            valores["fondo"] = nuevo_fondo
        if carnet_fondo:
            nuevo_carnet_fondo = media.guardar_imagen(carnet_fondo, "carnet_fondo", normalizar=False)
            valores["carnet_fondo"] = nuevo_carnet_fondo
        if trasera_fondo:
            nuevo_trasera_fondo = media.guardar_imagen(trasera_fondo, "trasera_fondo", normalizar=False)
            valores["trasera_fondo"] = nuevo_trasera_fondo
        if trasera_logo:
            nuevo_trasera_logo = media.guardar_imagen(trasera_logo, "trasera_logo", normalizar=False)
            valores["trasera_logo"] = nuevo_trasera_logo

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
        if titulo and existing and existing["titulo"] and existing["titulo"] != nuevo_titulo:
            media.eliminar_archivo(existing["titulo"])
        if trasera_fondo and existing and existing["trasera_fondo"] and existing["trasera_fondo"] != nuevo_trasera_fondo:
            media.eliminar_archivo(existing["trasera_fondo"])
        if trasera_logo and existing and existing["trasera_logo"] and existing["trasera_logo"] != nuevo_trasera_logo:
            media.eliminar_archivo(existing["trasera_logo"])
    finally:
        conn.close()
    return {"ok": True}
