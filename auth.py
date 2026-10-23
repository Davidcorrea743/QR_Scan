import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, Request

import database

_SECRET_KEY_ENV = os.environ.get("SECRET_KEY")
if _SECRET_KEY_ENV:
    SECRET_KEY = _SECRET_KEY_ENV
else:
    # Clave efímera: impredecible (no la default de siempre), pero los tokens
    # caducan al reiniciar. Obliga a definir SECRET_KEY en producción.
    SECRET_KEY = secrets.token_urlsafe(32)
    print(
        "⚠️  SECRET_KEY no está definida en el entorno; se generó una clave efímera.\n"
        "    Los tokens JWT caducarán al reiniciar el servidor.\n"
        "    Define la variable SECRET_KEY antes de un despliegue real."
    )

ALGORITHM = "HS256"
TOKEN_EXPIRATION_HOURS = 12
PBKDF2_ITERATIONS = 120_000
LONGITUD_MINIMA_PASSWORD = 8


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


def validar_password_nueva(password: str):
    """Valida la política de contraseñas del backend (mínimo 8 caracteres)."""
    if not password or len(password) < LONGITUD_MINIMA_PASSWORD:
        raise HTTPException(
            status_code=400,
            detail=f"La contraseña debe tener al menos {LONGITUD_MINIMA_PASSWORD} caracteres.",
        )


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


def get_current_user(
    authorization: str = Header(default=None),
    request: Request = None,
):
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
    if user["debe_cambiar_password"]:
        ruta = request.url.path if request is not None else ""
        if ruta not in ("/api/password", "/api/me"):
            raise HTTPException(
                status_code=403,
                detail="Debes cambiar tu contraseña antes de continuar",
            )
    return user


def es_super_admin(user) -> bool:
    """True si el usuario ve y gestiona todas las empresas."""
    return user["rol"] == "super_admin"


def es_admin(user) -> bool:
    """True si el usuario tiene privilegios de administrador (admin o super_admin)."""
    return user["rol"] in ("admin", "super_admin")


def en_alcance(user, empresa_id) -> bool:
    """True si el usuario puede ver/editar datos de esa empresa.

    super_admin ve todas; admin y editor solo la suya. No aplica a usuarios:
    ahí se usa en_alcance_usuario (los super_admin nunca los exponen).
    """
    return es_super_admin(user) or empresa_id == user["empresa_id"]


def exigir_en_alcance(user, empresa_id, detalle="No encontrado"):
    """404 si el dato pertenece a otra empresa (no revela su existencia)."""
    if not en_alcance(user, empresa_id):
        raise HTTPException(status_code=404, detail=detalle)


def empresa_escrita(user, empresa_id=None) -> int:
    """Resuelve la empresa de destino de una creación.

    - super_admin: la que indique (validada) o la suya por defecto.
    - admin: solo la suya (403 si intenta usar otra).
    """
    if not es_super_admin(user):
        if empresa_id is not None and empresa_id != user["empresa_id"]:
            raise HTTPException(
                status_code=403, detail="No puedes operar sobre otra empresa"
            )
        return user["empresa_id"]
    objetivo = empresa_id if empresa_id is not None else user["empresa_id"]
    conn = database.get_connection()
    try:
        existe = conn.execute("SELECT id FROM empresa WHERE id = ?", (objetivo,)).fetchone()
    finally:
        conn.close()
    if not existe:
        raise HTTPException(status_code=400, detail="Empresa no encontrada")
    return objetivo


def en_alcance_usuario(user, target) -> bool:
    """Alcance sobre otro usuario: super_admin ve a todos; un admin nunca ve
    (ni gestiona) a los super_admin, solo a los de su propia empresa."""
    if es_super_admin(user):
        return True
    return target["empresa_id"] == user["empresa_id"] and target["rol"] != "super_admin"


def empresa_del(user) -> int:
    """empresa_id al que pertenece el usuario (base para el aislamiento)."""
    return user["empresa_id"]


def require_auth(user=Depends(get_current_user)):
    return user


def require_admin(user=Depends(get_current_user)):
    if not es_admin(user):
        raise HTTPException(status_code=403, detail="Requiere rol administrador")
    return user


def require_super_admin(user=Depends(get_current_user)):
    if user["rol"] != "super_admin":
        raise HTTPException(status_code=403, detail="Requiere rol super administrador")
    return user
