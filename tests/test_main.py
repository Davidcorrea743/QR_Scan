def test_scan_registra_escaneo(client):
    r = client.get("/scan")
    assert r.status_code == 200
    data = r.json()
    assert "mensaje" in data

    registros = client.get("/registros").json()
    assert registros["total"] == 5


def test_registros_vacio(empty_client):
    r = empty_client.get("/registros")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["registros"] == []


def test_registros_filtro_fecha(client):
    r = client.get("/registros", params={"fecha": "2024-01-15"})
    data = r.json()
    assert data["total"] == 1
    assert data["registros"][0]["fecha"] == "2024-01-15"


def test_registros_filtro_mes(client):
    r = client.get("/registros", params={"mes": 1})
    data = r.json()
    assert data["total"] == 2


def test_registros_filtro_anio(client):
    r = client.get("/registros", params={"año": 2023})
    data = r.json()
    assert data["total"] == 1


def test_registros_filtro_rango_horas(client):
    r = client.get("/registros", params={"hora_inicio": 12, "hora_fin": 14})
    data = r.json()
    assert data["total"] == 1
    assert data["registros"][0]["hour"] == 14


def test_registros_filtros_combinados(client):
    r = client.get("/registros", params={"mes": 1, "hora_inicio": 9, "hora_fin": 18})
    data = r.json()
    assert data["total"] == 2


def test_registros_limit(client):
    r = client.get("/registros", params={"limit": 2})
    assert len(r.json()["registros"]) == 2


def test_estadisticas_por_dia(client):
    r = client.get("/estadisticas/por-dia")
    assert r.status_code == 200
    data = r.json()
    assert data["total_dias"] == 4
    assert all(d["total_escaneos"] == 1 for d in data["estadisticas_por_dia"])


def test_estadisticas_por_mes(client):
    r = client.get("/estadisticas/por-mes")
    data = r.json()
    total = sum(m["total_escaneos"] for m in data["estadisticas_por_mes"])
    assert total == 4


def test_estadisticas_por_hora(client):
    r = client.get("/estadisticas/por-hora")
    data = r.json()
    assert data["total_horas_con_actividad"] == 4


def test_estadisticas_por_anio(client):
    r = client.get("/estadisticas/por-año")
    data = r.json()
    assert data["total_años"] == 3


def test_estadisticas_resumen(client):
    r = client.get("/estadisticas/resumen")
    data = r.json()["resumen"]
    assert data["total_escaneos"] == 4
    assert data["escaneos_hoy"] == 1
    assert data["escaneos_este_mes"] == 1