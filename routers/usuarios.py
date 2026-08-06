from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import database
from auth import get_current_user, hash_password, require_admin

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    rol: str = "editor"


class ResetPasswordRequest(BaseModel):
    password: str


@router.get("")
def listar(user=Depends(require_admin)):
    conn = database.get_connection()
    try:
        rows = conn.execute(
            "SELECT id, username, rol, activo, debe_cambiar_password, created_at "
            "FROM usuarios ORDER BY username"
        ).fetchall()
    finally:
        conn.close()
    return {"usuarios": [dict(r) for r in rows]}


@router.post("")
def crear(body: CreateUserRequest, user=Depends(require_admin)):
    if body.rol not in ("admin", "editor"):
        raise HTTPException(status_code=400, detail="Rol inválido. Usa admin o editor.")
    conn = database.get_connection()
    try:
        exists = conn.execute(
            "SELECT id FROM usuarios WHERE username = ?", (body.username.strip(),)
        ).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="El usuario ya existe")
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, rol, debe_cambiar_password, activo) "
            "VALUES (?, ?, ?, 1, 1)",
            (body.username.strip(), hash_password(body.password), body.rol),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.put("/{user_id}/password")
def reset_password(
    user_id: int, body: ResetPasswordRequest, user=Depends(require_admin)
):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM usuarios WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        conn.execute(
            "UPDATE usuarios SET password_hash = ?, debe_cambiar_password = 1 WHERE id = ?",
            (hash_password(body.password), user_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.put("/{user_id}/estado")
def cambiar_estado(
    user_id: int, activo: int, user=Depends(require_admin)
):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propio usuario")
    conn = database.get_connection()
    try:
        conn.execute(
            "UPDATE usuarios SET activo = ? WHERE id = ?", (1 if activo else 0, user_id)
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
