from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import sqlite3
import os
from datetime import datetime
from typing import Optional

app = FastAPI(title="QR Tracker API", version="1.0.0")

# Servir la interfaz gráfica del generador en la raíz
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/styles.css", include_in_schema=False)
async def styles() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "styles.css"))

@app.get("/app.js", include_in_schema=False)
async def app_js() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "app.js"))

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Configuración de la base de datos SQLite (configurable por entorno para pruebas)
DB_PATH = os.environ.get("QR_DB_PATH", "qr_tracker.db")

def get_connection():
    try:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        return connection
    except Exception as e:
        print(f"Error conectando a SQLite: {e}")
        return None

def init_database():
    connection = get_connection()
    if connection:
        cursor = connection.cursor()
        try:
            # Crear tabla si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATE NOT NULL,
                    hora TIME NOT NULL,
                    ip VARCHAR(45),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    referer TEXT,
                    year INTEGER,
                    month INTEGER,
                    day INTEGER,
                    hour INTEGER
                )
            """)
            
            # Crear índices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fecha ON scans(fecha)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_year_month ON scans(year, month)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hour ON scans(hour)")
            
            connection.commit()
            print("✅ Base de datos SQLite inicializada correctamente")
        except Exception as e:
            print(f"Error inicializando base de datos: {e}")
        finally:
            cursor.close()
            connection.close()

# Inicializar la base de datos al arrancar
init_database()

# 🔹 Endpoint para registrar escaneo
@app.get("/scan")
async def scan_qr(request: Request):
    conn = get_connection()
    cursor = conn.cursor()

    ahora = datetime.now()
    fecha = ahora.date().isoformat()
    hora = ahora.time().isoformat()
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    referer = request.headers.get("referer", "")

    cursor.execute(
        "INSERT INTO scans (fecha, hora, ip, user_agent, referer, year, month, day, hour) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
        (fecha, hora, ip, user_agent, referer, ahora.year, ahora.month, ahora.day, ahora.hour)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return {
        "mensaje": "✅ Escaneo registrado exitosamente",
        "fecha": str(fecha),
        "hora": str(hora),
        "ip": ip,
        "timestamp": ahora.isoformat()
    }

# 🔹 Endpoint para ver registros con filtros avanzados
@app.get("/registros")
async def ver_registros(
    fecha: Optional[str] = None,
    mes: Optional[int] = None,
    año: Optional[int] = None,
    hora_inicio: Optional[int] = None,
    hora_fin: Optional[int] = None,
    limit: Optional[int] = 100
):
    conn = get_connection()
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
    conn.close()

    return {
        "registros": registros,
        "total": len(registros),
        "filtros_aplicados": {
            "fecha": fecha,
            "mes": mes,
            "año": año,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin
        }
    }

# 🔹 Endpoint para estadísticas por día
@app.get("/estadisticas/por-dia")
async def estadisticas_por_dia(año: Optional[int] = None, mes: Optional[int] = None):
    conn = get_connection()
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
    conn.close()
    
    return {
        "estadisticas_por_dia": resultados,
        "total_dias": len(resultados)
    }

# 🔹 Endpoint para estadísticas por mes
@app.get("/estadisticas/por-mes")
async def estadisticas_por_mes(año: Optional[int] = None):
    conn = get_connection()
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
    conn.close()
    
    return {
        "estadisticas_por_mes": resultados,
        "total_meses": len(resultados)
    }

# 🔹 Endpoint para estadísticas por hora
@app.get("/estadisticas/por-hora")
async def estadisticas_por_hora(fecha: Optional[str] = None):
    conn = get_connection()
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
    conn.close()
    
    return {
        "estadisticas_por_hora": resultados,
        "total_horas_con_actividad": len(resultados)
    }

# 🔹 Endpoint para estadísticas por año
@app.get("/estadisticas/por-año")
async def estadisticas_por_año():
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT year, COUNT(*) as total_escaneos FROM scans GROUP BY year ORDER BY year DESC"
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {
        "estadisticas_por_año": resultados,
        "total_años": len(resultados)
    }

# 🔹 Endpoint para resumen general de estadísticas
@app.get("/estadisticas/resumen")
async def resumen_estadisticas():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total de escaneos
    cursor.execute("SELECT COUNT(*) as total FROM scans")
    total_escaneos = cursor.fetchone()["total"]
    
    # Escaneos hoy
    cursor.execute("SELECT COUNT(*) as hoy FROM scans WHERE fecha = date('now')")
    escaneos_hoy = cursor.fetchone()["hoy"]
    
    # Escaneos esta semana
    cursor.execute("SELECT COUNT(*) as semana FROM scans WHERE date(fecha) >= date('now', 'weekday 0', '-7 days')")
    escaneos_semana = cursor.fetchone()["semana"]
    
    # Escaneos este mes
    cursor.execute("SELECT COUNT(*) as mes FROM scans WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')")
    escaneos_mes = cursor.fetchone()["mes"]
    
    # Hora más activa
    cursor.execute("SELECT hour, COUNT(*) as total FROM scans GROUP BY hour ORDER BY total DESC LIMIT 1")
    hora_mas_activa = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return {
        "resumen": {
            "total_escaneos": total_escaneos,
            "escaneos_hoy": escaneos_hoy,
            "escaneos_esta_semana": escaneos_semana,
            "escaneos_este_mes": escaneos_mes,
            "hora_mas_activa": hora_mas_activa["hour"] if hora_mas_activa else None,
            "escaneos_hora_mas_activa": hora_mas_activa["total"] if hora_mas_activa else 0
        }
    }
