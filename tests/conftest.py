import os
import sys
import tempfile
import uuid
from datetime import date

# Configurar las rutas de la BD y de uploads ANTES de importar los módulos de la
# app, porque éstos leen ${QR_DB_PATH} y ${QR_UPLOADS_DIR} en tiempo de
# importación. Así los tests nunca tocan la BD ni la carpeta reales.
_TEST_DB = os.path.join(tempfile.gettempdir(), f"qr_test_{uuid.uuid4().hex}.db")
os.environ["QR_DB_PATH"] = _TEST_DB
_TEST_UPLOADS = os.path.join(tempfile.gettempdir(), f"qr_test_uploads_{uuid.uuid4().hex}")
os.environ["QR_UPLOADS_DIR"] = _TEST_UPLOADS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient

import database
import main
import rate_limit
from estadisticas import main as stats_main


def _init_fresh():
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    database.init_database()
    rate_limit.limpiar()


def _seed_scans():
    conn = database.get_connection()
    cur = conn.cursor()
    hoy = date.today()
    rows = [
        ("2024-01-15", "10:00:00", 2024, 1, 15, 10),
        ("2024-01-16", "14:30:00", 2024, 1, 16, 14),
        ("2023-06-01", "09:15:00", 2023, 6, 1, 9),
        (hoy.isoformat(), "08:00:00", hoy.year, hoy.month, hoy.day, 8),
    ]
    for fecha, hora, year, month, day, hour in rows:
        cur.execute(
            "INSERT INTO scans (fecha, hora, ip, user_agent, referer, year, month, day, hour) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fecha, hora, "127.0.0.1", "test-agent", "", year, month, day, hour),
        )
    conn.commit()
    cur.close()
    conn.close()


@pytest.fixture
def client():
    _init_fresh()
    _seed_scans()
    return TestClient(main.app)


@pytest.fixture
def empty_client():
    _init_fresh()
    return TestClient(main.app)


@pytest.fixture
def stats_client():
    _init_fresh()
    _seed_scans()
    return TestClient(stats_main.app)


@pytest.fixture
def admin_token(client):
    res = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    # El admin recién creado tiene debe_cambiar_password=1, lo que bloquea el
    # uso de la API. Lo limpiamos (cambiando a la misma clave) para que el token
    # sirva en los endpoints protegidos, como si el admin ya hubiera completado
    # su primer acceso.
    res = client.post(
        "/api/password",
        json={"password_actual": "admin123", "password_nueva": "admin123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    return token


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def stats_auth_headers(stats_client):
    res = stats_client.post(
        "/api/login", json={"username": "admin", "password": "admin123"}
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    # Limpiamos debe_cambiar_password directamente en la BD (el cambio se haría
    # en la app principal 8000; aquí solo validamos el acceso al dashboard).
    conn = database.get_connection()
    try:
        conn.execute("UPDATE usuarios SET debe_cambiar_password = 0 WHERE username = 'admin'")
        conn.commit()
    finally:
        conn.close()
    return {"Authorization": f"Bearer {token}"}
