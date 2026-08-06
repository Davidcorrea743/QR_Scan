from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import os

import database
from routers import auth, empleados, empresa, paginas, usuarios

app = FastAPI(title="Carnet QR - Empresa", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(database.BASE_DIR, "static")), name="static")
app.mount("/uploads", StaticFiles(directory=database.UPLOADS_DIR), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(empleados.router, prefix="/api")
app.include_router(empresa.router, prefix="/api")
app.include_router(paginas.router)

database.init_database()


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/login")


# 🔹 Endpoint para registrar escaneo
@app.get("/scan")
async def scan_qr(request: Request):
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        ahora = datetime.now()
        fecha = ahora.date().isoformat()
        hora = ahora.time().isoformat()
        ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        referer = request.headers.get("referer", "")

        cursor.execute(
            "INSERT INTO scans (fecha, hora, ip, user_agent, referer, year, month, day, hour) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fecha, hora, ip, user_agent, referer, ahora.year, ahora.month, ahora.day, ahora.hour),
        )
        conn.commit()
        cursor.close()
    finally:
        conn.close()

    return {
        "mensaje": "✅ Escaneo registrado exitosamente",
        "fecha": fecha,
        "hora": hora,
        "ip": ip,
        "timestamp": ahora.isoformat(),
    }


# 🔹 Endpoint para ver registros con filtros avanzados
@app.get("/registros")
async def ver_registros(
    fecha: Optional[str] = None,
    mes: Optional[int] = None,
    año: Optional[int] = None,
    hora_inicio: Optional[int] = None,
    hora_fin: Optional[int] = None,
    limit: Optional[int] = 100,
):
    conn = database.get_connection()
    try:
        cursor = conn.cursor()

        query = "SELECT * FROM scans WHERE 1=1"
        params = []

        if fecha:
            query += " AND fecha = ?"
            params.append(fecha)

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

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        registros = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return {
        "registros": registros,
        "total": len(registros),
        "filtros_aplicados": {
            "fecha": fecha,
            "mes": mes,
            "año": año,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
        },
    }


# 🔹 Endpoint para estadísticas por día
@app.get("/estadisticas/por-dia")
async def estadisticas_por_dia(año: Optional[int] = None, mes: Optional[int] = None):
    conn = database.get_connection()
    try:
        cursor = conn.cursor()

        query = "SELECT fecha, COUNT(*) as total_escaneos FROM scans WHERE 1=1"
        params = []

        if año:
            query += " AND year = ?"
            params.append(año)

        if mes:
            query += " AND month = ?"
            params.append(mes)

        query += " GROUP BY fecha ORDER BY fecha DESC"

        cursor.execute(query, params)
        resultados = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return {
        "estadisticas_por_dia": resultados,
        "total_dias": len(resultados),
    }


# 🔹 Endpoint para estadísticas por mes
@app.get("/estadisticas/por-mes")
async def estadisticas_por_mes(año: Optional[int] = None):
    conn = database.get_connection()
    try:
        cursor = conn.cursor()

        query = "SELECT year, month, COUNT(*) as total_escaneos FROM scans WHERE 1=1"
        params = []

        if año:
            query += " AND year = ?"
            params.append(año)

        query += " GROUP BY year, month ORDER BY year DESC, month DESC"

        cursor.execute(query, params)
        resultados = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return {
        "estadisticas_por_mes": resultados,
        "total_meses": len(resultados),
    }


# 🔹 Endpoint para estadísticas por hora
@app.get("/estadisticas/por-hora")
async def estadisticas_por_hora(fecha: Optional[str] = None):
    conn = database.get_connection()
    try:
        cursor = conn.cursor()

        query = "SELECT hour, COUNT(*) as total_escaneos FROM scans WHERE 1=1"
        params = []

        if fecha:
            query += " AND fecha = ?"
            params.append(fecha)

        query += " GROUP BY hour ORDER BY hour ASC"

        cursor.execute(query, tuple(params))
        resultados = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return {
        "estadisticas_por_hora": resultados,
        "total_horas_con_actividad": len(resultados),
    }


# 🔹 Endpoint para estadísticas por año
@app.get("/estadisticas/por-año")
async def estadisticas_por_año():
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT year, COUNT(*) as total_escaneos FROM scans GROUP BY year ORDER BY year DESC"
        cursor.execute(query)
        resultados = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return {
        "estadisticas_por_año": resultados,
        "total_años": len(resultados),
    }


# 🔹 Endpoint para resumen general de estadísticas
@app.get("/estadisticas/resumen")
async def resumen_estadisticas():
    conn = database.get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM scans")
        total_escaneos = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as hoy FROM scans WHERE fecha = date('now')")
        escaneos_hoy = cursor.fetchone()["hoy"]

        cursor.execute(
            "SELECT COUNT(*) as semana FROM scans WHERE date(fecha) >= date('now', 'weekday 0', '-7 days')"
        )
        escaneos_semana = cursor.fetchone()["semana"]

        cursor.execute(
            "SELECT COUNT(*) as mes FROM scans WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')"
        )
        escaneos_mes = cursor.fetchone()["mes"]

        cursor.execute(
            "SELECT hour, COUNT(*) as total FROM scans GROUP BY hour ORDER BY total DESC LIMIT 1"
        )
        hora_mas_activa = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    return {
        "resumen": {
            "total_escaneos": total_escaneos,
            "escaneos_hoy": escaneos_hoy,
            "escaneos_esta_semana": escaneos_semana,
            "escaneos_este_mes": escaneos_mes,
            "hora_mas_activa": hora_mas_activa["hour"] if hora_mas_activa else None,
            "escaneos_hora_mas_activa": hora_mas_activa["total"] if hora_mas_activa else 0,
        }
    }
