from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

import database
import media
from auth import get_current_user, require_admin

router = APIRouter(prefix="/empleados", tags=["empleados"])

CAMPOS_EDITOR = {"telefono", "correo"}


@router.get("")
def listar(incluir_inactivos: int = 0, user=Depends(get_current_user)):
    conn = database.get_connection()
    try:
        if incluir_inactivos and user["rol"] == "admin":
            rows = conn.execute(
                "SELECT * FROM empleados ORDER BY nombre, apellido"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM empleados WHERE activo = 1 ORDER BY nombre, apellido"
            ).fetchall()
    finally:
        conn.close()
    return {"empleados": [dict(r) for r in rows]}


@router.get("/{emp_id}")
def obtener(emp_id: int, user=Depends(get_current_user)):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return dict(row)


@router.post("")
def crear(
    nombre: str = Form(...),
    apellido: str = Form(...),
    cedula: str = Form(""),
    cargo: str = Form(""),
    correo: str = Form(""),
    telefono: str = Form(""),
    foto: UploadFile = File(None),
    user=Depends(require_admin),
):
    nombre_foto = media.guardar_imagen(foto, "empleado") if foto else None
    conn = database.get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO empleados (nombre, apellido, cedula, cargo, correo, telefono, foto) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                nombre.strip(),
                apellido.strip(),
                cedula.strip(),
                cargo.strip(),
                correo.strip(),
                telefono.strip(),
                nombre_foto,
            ),
        )
        conn.commit()
        emp_id = cur.lastrowid
    finally:
        conn.close()
    return {"id": emp_id}


@router.put("/{emp_id}")
def actualizar(
    emp_id: int,
    nombre: str = Form(None),
    apellido: str = Form(None),
    cedula: str = Form(None),
    cargo: str = Form(None),
    correo: str = Form(None),
    telefono: str = Form(None),
    foto: UploadFile = File(None),
    user=Depends(get_current_user),
):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")

        valores = {}
        if user["rol"] == "admin":
            for k, v in (
                ("nombre", nombre),
                ("apellido", apellido),
                ("cedula", cedula),
                ("cargo", cargo),
                ("correo", correo),
                ("telefono", telefono),
            ):
                if v is not None:
                    valores[k] = v.strip()
        else:
            for k in CAMPOS_EDITOR:
                v = {"telefono": telefono, "correo": correo}[k]
                if v is not None:
                    valores[k] = v.strip()

        if foto:
            nuevo = media.guardar_imagen(foto, "empleado")
            valores["foto"] = nuevo

        if not valores:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")

        sets = ", ".join(f"{k} = ?" for k in valores)
        conn.execute(
            f"UPDATE empleados SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*valores.values(), emp_id),
        )
        conn.commit()
        if foto and row["foto"] and row["foto"] != nuevo:
            media.eliminar_archivo(row["foto"])
    finally:
        conn.close()
    return {"ok": True, "id": emp_id}


@router.delete("/{emp_id}")
def desactivar(emp_id: int, user=Depends(require_admin)):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        conn.execute(
            "UPDATE empleados SET activo = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (emp_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.post("/{emp_id}/restaurar")
def restaurar(emp_id: int, user=Depends(require_admin)):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        conn.execute(
            "UPDATE empleados SET activo = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (emp_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
