import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# QR_UPLOADS_DIR permite apuntar a otra carpeta (tests la aíslan en un tmp).
UPLOADS_DIR = os.environ.get("QR_UPLOADS_DIR", os.path.join(BASE_DIR, "uploads"))
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
    _normalizar_datos(conn)
    _seed_admin(conn)
    conn.close()


def _agregar_columna(conn, tabla: str, columna: str, definicion: str):
    """ALTER TABLE ADD COLUMN idempotente (solo si la columna no existe)."""
    cur = conn.cursor()
    existentes = [row["name"] for row in cur.execute(f"PRAGMA table_info({tabla})")]
    if columna not in existentes:
        cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
        conn.commit()
    cur.close()


def _empresa_multifila(conn):
    """Quita el CHECK (id = 1) de la tabla empresa para permitir varias filas.

    SQLite no permite eliminar un CHECK con ALTER: se recrea la tabla
    conservando datos y columnas. Idempotente: solo actúa si el CHECK existe.
    """
    cur = conn.cursor()
    fila = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'empresa'"
    ).fetchone()
    sql = fila[0] if fila else None
    if not sql or "check" not in sql.lower():
        cur.close()
        return

    columnas = [
        (row["name"], row["type"] or "TEXT")
        for row in cur.execute("PRAGMA table_info(empresa)")
    ]
    tipos_validos = {"TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"}
    definiciones = []
    for nombre, tipo in columnas:
        if nombre == "id":
            definiciones.append("id INTEGER PRIMARY KEY")
        else:
            tipo_sql = tipo.upper() if tipo.upper() in tipos_validos else "TEXT"
            definiciones.append(f"{nombre} {tipo_sql}")
    nombres = ", ".join(n for n, _ in columnas)
    cur.executescript(
        f"""
        CREATE TABLE empresa_tmp ({", ".join(definiciones)});
        INSERT INTO empresa_tmp ({nombres}) SELECT {nombres} FROM empresa;
        DROP TABLE empresa;
        ALTER TABLE empresa_tmp RENAME TO empresa;
        """
    )
    conn.commit()
    cur.close()


def _migrar_columnas(conn):
    """Migración de esquema multi-empresa (idempotente): en cada arranque."""
    cur = conn.cursor()
    # 1) columnas de la configuración de empresa (previas a reconstruir la tabla)
    for columna in ("carnet_fondo", "titulo", "ubicacion", "galeria"):
        columnas = [row["name"] for row in cur.execute("PRAGMA table_info(empresa)")]
        if columna not in columnas:
            cur.execute(f"ALTER TABLE empresa ADD COLUMN {columna} TEXT")
            conn.commit()
    for columna in (
        "trasera_fondo", "trasera_logo", "trasera_mensaje",
        "trasera_correo", "trasera_telefono", "trasera_rif",
    ):
        columnas = [row["name"] for row in cur.execute("PRAGMA table_info(empresa)")]
        if columna not in columnas:
            cur.execute(f"ALTER TABLE empresa ADD COLUMN {columna} TEXT")
            conn.commit()
    cur.close()

    # 2) empresa con varias filas (elimina CHECK id = 1)
    _empresa_multifila(conn)

    # empresa por defecto para bases de datos nuevas o vacías
    conn.execute(
        "INSERT OR IGNORE INTO empresa (id, nombre) VALUES (1, 'Empresa 1')"
    )
    conn.commit()

    # 3) pertenencia a empresa en empleados, usuarios y scans (+ A3: empleado)
    #    Nota: SQLite prohíbe REFERENCES con default NO-NULL en ADD COLUMN, así
    #    que empresa_id se controla con índices + validación en la API; la FK de
    #    empleado_id sí es posible porque su default es NULL.
    _agregar_columna(conn, "empleados", "empresa_id", "INTEGER NOT NULL DEFAULT 1")
    _agregar_columna(conn, "usuarios", "empresa_id", "INTEGER NOT NULL DEFAULT 1")
    _agregar_columna(conn, "scans", "empresa_id", "INTEGER NOT NULL DEFAULT 1")
    _agregar_columna(conn, "scans", "empleado_id", "INTEGER REFERENCES empleados(id)")

    # 4) índices de consulta
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_empleados_empresa ON empleados(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_usuarios_empresa ON usuarios(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_scans_empresa ON scans(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_scans_empleado ON scans(empleado_id);
        """
    )

    # 5) migración de roles: si aún no hay super_admin, los admin pasan a
    #    super_admin (una sola vez; los admin creados después se conservan)
    conn.execute(
        "UPDATE usuarios SET rol = 'super_admin' WHERE rol = 'admin' "
        "AND NOT EXISTS (SELECT 1 FROM usuarios WHERE rol = 'super_admin')"
    )
    conn.commit()


def _normalizar_datos(conn):
    """Normaliza datos existentes (idempotente): se ejecuta en cada arranque y
    solo actualiza las filas cuyo texto cambia con la normalización."""
    from normalizar import normalizar_correo, normalizar_nombre

    cur = conn.cursor()
    for row in cur.execute(
        "SELECT id, nombre, apellido, cargo, correo FROM empleados"
    ).fetchall():
        nuevo_nombre = normalizar_nombre(row["nombre"])
        nuevo_apellido = normalizar_nombre(row["apellido"])
        nuevo_cargo = normalizar_nombre(row["cargo"], conservar_siglas=True)
        nuevo_correo = normalizar_correo(row["correo"])
        if (nuevo_nombre, nuevo_apellido, nuevo_cargo, nuevo_correo) != (
            row["nombre"],
            row["apellido"],
            row["cargo"],
            row["correo"],
        ):
            cur.execute(
                "UPDATE empleados SET nombre = ?, apellido = ?, cargo = ?, correo = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (nuevo_nombre, nuevo_apellido, nuevo_cargo, nuevo_correo, row["id"]),
            )
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
            ("admin", hash_password("admin123"), "super_admin", 1),
        )
        conn.commit()
        print("✅ Usuario admin creado: admin / admin123 (cambiar en el primer acceso)")
    cur.close()
