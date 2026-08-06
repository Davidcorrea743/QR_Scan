import os
import sys
import tempfile
import uuid
from datetime import date

# Configurar la ruta de la BD ANTES de importar los módulos de la app,
# porque éstos leen ${QR_DB_PATH} en tiempo de importación.
_TEST_DB = os.path.join(tempfile.gettempdir(), f"qr_test_{uuid.uuid4().hex}.db")
os.environ["QR_DB_PATH"] = _TEST_DB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient

import database
import main
from estadisticas import main as stats_main


def _init_fresh():
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    database.init_database()


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
    return res.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
