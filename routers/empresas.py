from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import database
from auth import require_super_admin

router = APIRouter(prefix="/empresas", tags=["empresas"])


class CrearEmpresaRequest(BaseModel):
    nombre: str


class RenombrarEmpresaRequest(BaseModel):
    nombre: str


@router.get("")
def listar(user=Depends(require_super_admin)):
    """Lista todas las empresas (solo super_admin)."""
    conn = database.get_connection()
    try:
        filas = conn.execute(
            "SELECT e.id, e.nombre, "
            "(SELECT COUNT(*) FROM empleados WHERE empresa_id = e.id AND activo = 1) AS empleados "
            "FROM empresa e ORDER BY e.id"
        ).fetchall()
    finally:
        conn.close()
    return {"empresas": [dict(f) for f in filas]}


@router.post("")
def crear(body: CrearEmpresaRequest, user=Depends(require_super_admin)):
    nombre = (body.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    conn = database.get_connection()
    try:
        existe = conn.execute(
            "SELECT id FROM empresa WHERE LOWER(nombre) = LOWER(?)", (nombre,)
        ).fetchone()
        if existe:
            raise HTTPException(status_code=400, detail="Ya existe una empresa con ese nombre")
        cur = conn.execute("INSERT INTO empresa (nombre) VALUES (?)", (nombre,))
        conn.commit()
        nueva_id = cur.lastrowid
    finally:
        conn.close()
    return {"id": nueva_id, "nombre": nombre}


@router.put("/{empresa_id}")
def renombrar(empresa_id: int, body: RenombrarEmpresaRequest, user=Depends(require_super_admin)):
    nombre = (body.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    conn = database.get_connection()
    try:
        fila = conn.execute("SELECT id FROM empresa WHERE id = ?", (empresa_id,)).fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        conn.execute("UPDATE empresa SET nombre = ? WHERE id = ?", (nombre, empresa_id))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
