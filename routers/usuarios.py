from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import database
from auth import (
    empresa_escrita,
    en_alcance_usuario,
    es_super_admin,
    get_current_user,
    hash_password,
    require_admin,
    validar_password_nueva,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    rol: str = "editor"
    empresa_id: int = None


class ResetPasswordRequest(BaseModel):
    password: str


def _exigir_usuario_en_alcance(user, row, detalle="Usuario no encontrado"):
    if not row or not en_alcance_usuario(user, row):
        # 404: un admin no debe saber si el usuario existe en otra empresa
        raise HTTPException(status_code=404, detail=detalle)


@router.get("")
def listar(
    page: int = 1,
    limit: int = 10,
    empresa_id: int = None,
    user=Depends(require_admin),
):
    page = max(1, page)
    limit = max(1, min(limit, 200))
    offset = (page - 1) * limit

    condiciones = []
    params = []
    if es_super_admin(user):
        # super_admin: todos los usuarios (o los de una empresa con ?empresa_id=)
        if empresa_id is not None:
            condiciones.append("empresa_id = ?")
            params.append(empresa_id)
    else:
        # admin: los de su empresa; nunca los super_admin
        condiciones += ["empresa_id = ?", "rol != 'super_admin'"]
        params.append(user["empresa_id"])
    where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""

    conn = database.get_connection()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM usuarios{where}", params
        ).fetchone()["n"]
        rows = conn.execute(
            "SELECT id, username, rol, empresa_id, activo, debe_cambiar_password, created_at "
            f"FROM usuarios{where} ORDER BY username LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    finally:
        conn.close()
    return {
        "usuarios": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
    }


@router.post("")
def crear(body: CreateUserRequest, user=Depends(require_admin)):
    if body.rol not in ("admin", "editor"):
        raise HTTPException(
            status_code=400,
            detail="Rol inválido. Usa admin o editor.",
        )
    validar_password_nueva(body.password)
    destino = empresa_escrita(user, body.empresa_id)
    conn = database.get_connection()
    try:
        exists = conn.execute(
            "SELECT id FROM usuarios WHERE username = ?", (body.username.strip(),)
        ).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="El usuario ya existe")
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, rol, empresa_id, "
            "debe_cambiar_password, activo) VALUES (?, ?, ?, ?, 1, 1)",
            (body.username.strip(), hash_password(body.password), body.rol, destino),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "empresa_id": destino}


@router.put("/{user_id}/password")
def reset_password(
    user_id: int, body: ResetPasswordRequest, user=Depends(require_admin)
):
    validar_password_nueva(body.password)
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT id, empresa_id, rol FROM usuarios WHERE id = ?", (user_id,)
        ).fetchone()
        _exigir_usuario_en_alcance(user, row)
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
        row = conn.execute(
            "SELECT id, empresa_id, rol FROM usuarios WHERE id = ?", (user_id,)
        ).fetchone()
        _exigir_usuario_en_alcance(user, row)
        conn.execute(
            "UPDATE usuarios SET activo = ? WHERE id = ?", (1 if activo else 0, user_id)
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
