from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import database
from auth import create_token, get_current_user, hash_password, verify_password

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


@router.post("/login")
def login(body: LoginRequest):
    conn = database.get_connection()
    try:
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ?", (body.username.strip(),)
        ).fetchone()
    finally:
        conn.close()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if not user["activo"]:
        raise HTTPException(status_code=401, detail="Usuario inactivo")
    return {
        "access_token": create_token(user),
        "token_type": "bearer",
        "username": user["username"],
        "rol": user["rol"],
        "debe_cambiar_password": user["debe_cambiar_password"],
    }


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "username": user["username"],
        "rol": user["rol"],
        "debe_cambiar_password": user["debe_cambiar_password"],
    }


@router.post("/password")
def cambiar_password(body: ChangePasswordRequest, user=Depends(get_current_user)):
    conn = database.get_connection()
    try:
        current = conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (user["id"],)
        ).fetchone()
        if not verify_password(body.password_actual, current["password_hash"]):
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
        new_hash = hash_password(body.password_nueva)
        conn.execute(
            "UPDATE usuarios SET password_hash = ?, debe_cambiar_password = 0 WHERE id = ?",
            (new_hash, user["id"]),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
