def test_registros_sin_filtros(stats_client):
    r = stats_client.get("/registros")
    assert r.status_code == 200
    assert r.json()["total"] == 4


def test_registros_filtro_mes(stats_client):
    r = stats_client.get("/registros", params={"mes": 1})
    assert r.json()["total"] == 2


def test_registros_filtro_anio(stats_client):
    r = stats_client.get("/registros", params={"año": 2023})
    assert r.json()["total"] == 1


def test_registros_filtro_fecha(stats_client):
    r = stats_client.get("/registros", params={"fecha": "2023-06-01"})
    data = r.json()
    assert data["total"] == 1
    assert data["registros"][0]["fecha"] == "2023-06-01"


def test_registros_filtro_rango_horas(stats_client):
    r = stats_client.get("/registros", params={"hora_inicio": 12, "hora_fin": 14})
    data = r.json()
    assert data["total"] == 1
    assert data["registros"][0]["hour"] == 14


def test_estadisticas_resumen(stats_client):
    r = stats_client.get("/estadisticas")
    assert r.status_code == 200
    data = r.json()
    assert data["total_escaneos"] == 4
    assert len(data["escaneos_por_dia"]) >= 1
    assert len(data["escaneos_por_hora_hoy"]) >= 1