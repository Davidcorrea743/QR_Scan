import database


def _contar_scans():
    conn = database.get_connection()
    try:
        return conn.execute("SELECT COUNT(*) AS c FROM scans").fetchone()["c"]
    finally:
        conn.close()


def test_scan_registra_escaneo(client):
    antes = _contar_scans()
    r = client.get("/scan")
    assert r.status_code == 200
    data = r.json()
    assert "mensaje" in data
    assert _contar_scans() == antes + 1


def test_scan_registra_timestamp_local(client):
    from datetime import datetime

    r = client.get("/scan")
    assert r.status_code == 200

    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT fecha, hora, timestamp, hour FROM scans ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    # timestamp en hora local: coincide con fecha/hora de la misma fila...
    assert row["timestamp"][:10] == row["fecha"]
    assert int(row["timestamp"][11:13]) == row["hour"]
    # ...y cercano a la hora local actual (no desplazado por el huso UTC)
    ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
    assert abs((datetime.now() - ts).total_seconds()) < 60


def test_registros_y_estadisticas_eliminados_de_8000(client):
    # Estas rutas se movieron al dashboard del puerto 8001; en 8000 ya no existen.
    assert client.get("/registros").status_code == 404
    assert client.get("/estadisticas/resumen").status_code == 404
    assert client.get("/estadisticas/por-dia").status_code == 404


def test_scan_rate_limit(client):
    # Límite por defecto: 30/min por IP. La 31ª petición debe ser 429.
    for _ in range(30):
        assert client.get("/scan").status_code == 200
    assert client.get("/scan").status_code == 429
