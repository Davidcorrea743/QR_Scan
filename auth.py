import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException

import database

SECRET_KEY = os.environ.get("SECRET_KEY", "carnet-qr-secret-cambiar-en-produccion")
ALGORITHM = "HS256"
TOKEN_EXPIRATION_HOURS = 12
PBKDF2_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def create_token(user) -> str:
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "rol": user["rol"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def get_current_user(authorization: str = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")
    payload = _decode_token(authorization.split(" ", 1)[1])
    conn = database.get_connection()
    try:
        user = conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (int(payload["sub"]),)
        ).fetchone()
    finally:
        conn.close()
    if not user or not user["activo"]:
        raise HTTPException(status_code=401, detail="Usuario inactivo o inexistente")
    return user


def require_auth(user=Depends(get_current_user)):
    return user


def require_admin(user=Depends(get_current_user)):
    if user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Requiere rol administrador")
    return user
