from datetime import datetime

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import os

import database
import rate_limit
from routers import auth, empleados, empresa, empresas, paginas, usuarios

app = FastAPI(title="Carnet QR - Empresa", version="2.0.0")


@app.middleware("http")
async def headers_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.mount("/static", StaticFiles(directory=os.path.join(database.BASE_DIR, "static")), name="static")
app.mount("/uploads", StaticFiles(directory=database.UPLOADS_DIR), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(empleados.router, prefix="/api")
app.include_router(empresa.router, prefix="/api")
app.include_router(empresas.router, prefix="/api")
app.include_router(paginas.router)

database.init_database()


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/login")


@app.get("/scan", dependencies=[Depends(rate_limit.limitar_scan)])
async def scan_qr(request: Request, e: int = None):
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        ahora = datetime.now()
        fecha = ahora.date().isoformat()
        hora = ahora.time().isoformat()
        ip = request.client.host if request.client else ""
        user_agent = request.headers.get("user-agent", "")
        referer = request.headers.get("referer", "")

        # A3: el perfil envía el empleado (?e=) para vincular el escaneo
        empleado_id = None
        empresa_id = 1
        if e:
            emp = cursor.execute(
                "SELECT id, empresa_id FROM empleados WHERE id = ?", (e,)
            ).fetchone()
            if emp:
                empleado_id = emp["id"]
                empresa_id = emp["empresa_id"]

        cursor.execute(
            "INSERT INTO scans (fecha, hora, ip, user_agent, referer, timestamp, "
            "empleado_id, empresa_id, year, month, day, hour) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fecha,
                hora,
                ip,
                user_agent,
                referer,
                ahora.strftime("%Y-%m-%d %H:%M:%S"),
                empleado_id,
                empresa_id,
                ahora.year,
                ahora.month,
                ahora.day,
                ahora.hour,
            ),
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
