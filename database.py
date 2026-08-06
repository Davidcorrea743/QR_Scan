import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.environ.get("QR_DB_PATH", os.path.join(BASE_DIR, "qr_tracker.db"))

os.makedirs(UPLOADS_DIR, exist_ok=True)


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database():
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'editor',
            debe_cambiar_password INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            cedula TEXT,
            cargo TEXT,
            correo TEXT,
            telefono TEXT,
            foto TEXT,
            activo INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS empresa (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nombre TEXT,
            logo TEXT,
            fondo TEXT,
            redes TEXT
        );

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
        );

        CREATE INDEX IF NOT EXISTS idx_fecha ON scans(fecha);
        CREATE INDEX IF NOT EXISTS idx_year_month ON scans(year, month);
        CREATE INDEX IF NOT EXISTS idx_hour ON scans(hour);
        """
    )
    conn.commit()
    _migrar_columnas(conn)
    _seed_admin(conn)
    conn.close()


def _migrar_columnas(conn):
    """Agrega columnas nuevas a tablas existentes (migración simple)."""
    cur = conn.cursor()
    columnas = [row["name"] for row in cur.execute("PRAGMA table_info(empresa)").fetchall()]
    if "carnet_fondo" not in columnas:
        cur.execute("ALTER TABLE empresa ADD COLUMN carnet_fondo TEXT")
        conn.commit()
    columnas = [row["name"] for row in cur.execute("PRAGMA table_info(empresa)").fetchall()]
    if "titulo" not in columnas:
        cur.execute("ALTER TABLE empresa ADD COLUMN titulo TEXT")
        conn.commit()
    cur.close()


def _seed_admin(conn):
    from auth import hash_password

    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) AS c FROM usuarios").fetchone()["c"]
    if count == 0:
        cur.execute(
            "INSERT INTO usuarios (username, password_hash, rol, debe_cambiar_password, activo) "
            "VALUES (?, ?, ?, ?, 1)",
            ("admin", hash_password("admin123"), "admin", 1),
        )
        conn.commit()
        print("✅ Usuario admin creado: admin / admin123 (cambiar en el primer acceso)")
    cur.close()
