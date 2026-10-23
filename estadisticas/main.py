import os
import sys
from datetime import datetime, timedelta

# Permite importar los módulos de la raíz del proyecto (database, auth, rate_limit).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

import auth
import database
import rate_limit
from routers.empresas import router as empresas_router

app = FastAPI()
app.include_router(empresas_router, prefix="/api")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.middleware("http")
async def headers_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "registros.html"))


@app.get("/estilos.css", include_in_schema=False)
async def estilos() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "estilos.css"))


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login", dependencies=[Depends(rate_limit.limitar_login)])
def login(body: LoginRequest):
    conn = database.get_connection()
    try:
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ?", (body.username.strip(),)
        ).fetchone()
    finally:
        conn.close()
    if not user or not auth.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if not user["activo"]:
        raise HTTPException(status_code=401, detail="Usuario inactivo")
    return {
        "access_token": auth.create_token(user),
        "token_type": "bearer",
        "username": user["username"],
        "rol": user["rol"],
    }


def _alcance_empresa(user, empresa_id=None):
    """(condición SQL, params) que limita los scans a la empresa del usuario.

    super_admin: todas las empresas (o la que indique con ?empresa_id=);
    admin: solo los de su empresa.
    """
    if auth.es_super_admin(user):
        if empresa_id is not None:
            return " AND empresa_id = ?", [empresa_id]
        return "", []
    return " AND empresa_id = ?", [user["empresa_id"]]


def _construir_filtro_registros(fecha, hora, mes, año, hora_inicio, hora_fin, user, empresa_id=None):
    query = "SELECT * FROM scans WHERE 1=1"
    params = []

    if fecha:
        query += " AND fecha = ?"
        params.append(fecha)

    if hora:
        query += " AND hora >= ?"
        params.append(hora)

    if mes:
        query += " AND month = ?"
        params.append(mes)

    if año:
        query += " AND year = ?"
        params.append(año)

    if hora_inicio is not None:
        query += " AND hour >= ?"
        params.append(hora_inicio)

    if hora_fin is not None:
        query += " AND hour <= ?"
        params.append(hora_fin)

    cond_empresa, params_empresa = _alcance_empresa(user, empresa_id)
    query += cond_empresa
    params += params_empresa

    return query, params


@app.get("/registros")
def ver_registros(
    fecha: str = None,
    hora: str = None,
    mes: int = None,
    año: int = None,
    hora_inicio: int = None,
    hora_fin: int = None,
    empresa_id: int = None,
    limit: int = 10,
    page: int = 1,
    user=Depends(auth.require_admin),
):
    page = max(1, page)
    limit = max(1, min(limit, 500))
    offset = (page - 1) * limit

    query, params = _construir_filtro_registros(
        fecha, hora, mes, año, hora_inicio, hora_fin, user, empresa_id
    )

    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        total = cursor.execute(
            query.replace("SELECT *", "SELECT COUNT(*) AS n"), params
        ).fetchone()["n"]

        cursor.execute(query + " ORDER BY timestamp DESC LIMIT ? OFFSET ?", params + [limit, offset])
        registros = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return {
        "registros": registros,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
        "filtros_aplicados": {
            "fecha": fecha,
            "hora": hora,
            "mes": mes,
            "año": año,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "empresa_id": empresa_id if auth.es_super_admin(user) else user["empresa_id"],
        },
    }


@app.get("/estadisticas")
def obtener_estadisticas(empresa_id: int = None, user=Depends(auth.require_admin)):
    cond_empresa, params_empresa = _alcance_empresa(user, empresa_id)
    conn = database.get_connection()
    try:
        cursor = conn.cursor()

        # Total de escaneos
        cursor.execute(
            f"SELECT COUNT(*) as total FROM scans WHERE 1=1{cond_empresa}", params_empresa
        )
        total = cursor.fetchone()["total"]

        # Escaneos por día (últimos 7 días) — fechas en hora local (fecha lo guarda la app en local)
        hoy = datetime.now()
        hace_7_dias = (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute(
            f"""
            SELECT fecha, COUNT(*) as total_escaneos
            FROM scans
            WHERE fecha >= ?{cond_empresa}
            GROUP BY fecha
            ORDER BY fecha DESC
            """,
            [hace_7_dias, *params_empresa],
        )
        por_dia = cursor.fetchall()

        # Escaneos por hora (hoy)
        cursor.execute(
            f"""
            SELECT hour, COUNT(*) as total_escaneos
            FROM scans
            WHERE fecha = ?{cond_empresa}
            GROUP BY hour
            ORDER BY hour ASC
            """,
            [hoy.strftime("%Y-%m-%d"), *params_empresa],
        )
        por_hora = cursor.fetchall()

        cursor.close()
    finally:
        conn.close()

    return {
        "total_escaneos": total,
        "escaneos_por_dia": por_dia,
        "escaneos_por_hora_hoy": por_hora,
    }
