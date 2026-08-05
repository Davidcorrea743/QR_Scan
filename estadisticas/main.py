from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import sqlite3
import os

app = FastAPI()

# Servir el dashboard de estadísticas en la raíz
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "registros.html"))

@app.get("/estilos.css", include_in_schema=False)
async def estilos() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "estilos.css"))

# 🔹 Permitir que el frontend (HTML) pueda acceder
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Configuración de la base de datos SQLite (configurable por entorno para pruebas)
DB_PATH = os.environ.get("QR_DB_PATH", "../qr_tracker.db")

def get_connection():
    try:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        return connection
    except Exception as e:
        print(f"Error conectando a SQLite: {e}")
        return None

# 🔹 Endpoint que devuelve registros con filtros opcionales
@app.get("/registros")
async def ver_registros(
    fecha: str = None, 
    hora: str = None,
    mes: int = None,
    año: int = None,
    hora_inicio: int = None,
    hora_fin: int = None,
    limit: int = 100
):
    conn = get_connection()
    cursor = conn.cursor()

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

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    registros = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "registros": registros,
        "total": len(registros),
        "filtros_aplicados": {
            "fecha": fecha,
            "hora": hora,
            "mes": mes,
            "año": año,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin
        }
    }

# 🔹 Endpoint para estadísticas resumidas
@app.get("/estadisticas")
async def obtener_estadisticas():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total de escaneos
    cursor.execute("SELECT COUNT(*) as total FROM scans")
    total = cursor.fetchone()["total"]
    
    # Escaneos por día (últimos 7 días)
    cursor.execute("""
        SELECT fecha, COUNT(*) as total_escaneos 
        FROM scans 
        WHERE fecha >= date('now', '-7 days')
        GROUP BY fecha 
        ORDER BY fecha DESC
    """)
    por_dia = cursor.fetchall()
    
    # Escaneos por hora (hoy)
    cursor.execute("""
        SELECT hour, COUNT(*) as total_escaneos 
        FROM scans 
        WHERE fecha = date('now')
        GROUP BY hour 
        ORDER BY hour ASC
    """)
    por_hora = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {
        "total_escaneos": total,
        "escaneos_por_dia": por_dia,
        "escaneos_por_hora_hoy": por_hora
    }