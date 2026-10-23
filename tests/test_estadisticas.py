def test_registros_sin_filtros(stats_client, stats_auth_headers):
    r = stats_client.get("/registros", headers=stats_auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 4


def test_registros_filtro_mes(stats_client, stats_auth_headers):
    r = stats_client.get("/registros", params={"mes": 1}, headers=stats_auth_headers)
    assert r.json()["total"] == 2


def test_registros_filtro_anio(stats_client, stats_auth_headers):
    r = stats_client.get("/registros", params={"año": 2023}, headers=stats_auth_headers)
    assert r.json()["total"] == 1


def test_registros_filtro_fecha(stats_client, stats_auth_headers):
    r = stats_client.get(
        "/registros", params={"fecha": "2023-06-01"}, headers=stats_auth_headers
    )
    data = r.json()
    assert data["total"] == 1
    assert data["registros"][0]["fecha"] == "2023-06-01"


def test_registros_filtro_rango_horas(stats_client, stats_auth_headers):
    r = stats_client.get(
        "/registros", params={"hora_inicio": 12, "hora_fin": 14}, headers=stats_auth_headers
    )
    data = r.json()
    assert data["total"] == 1
    assert data["registros"][0]["hour"] == 14


def test_estadisticas_resumen(stats_client, stats_auth_headers):
    r = stats_client.get("/estadisticas", headers=stats_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_escaneos"] == 4
    assert len(data["escaneos_por_dia"]) >= 1
    assert len(data["escaneos_por_hora_hoy"]) >= 1


def test_estadisticas_usa_fecha_local(stats_client, stats_auth_headers):
    from datetime import date

    hoy = date.today().isoformat()
    r = stats_client.get("/estadisticas", headers=stats_auth_headers)
    assert r.status_code == 200
    data = r.json()

    # La fecha de hoy (local) debe aparecer entre los últimos 7 días...
    dias = [d["fecha"] for d in data["escaneos_por_dia"]]
    assert hoy in dias
    # ...y el scan sembrado de hoy (hora 8) debe contarse en las horas de hoy.
    horas = [h["hour"] for h in data["escaneos_por_hora_hoy"]]
    assert 8 in horas


def test_registros_paginacion(stats_client, stats_auth_headers):
    r = stats_client.get(
        "/registros", params={"limit": 2, "page": 1}, headers=stats_auth_headers
    )
    data = r.json()
    assert data["total"] == 4
    assert len(data["registros"]) == 2
    assert data["page"] == 1
    assert data["pages"] == 2

    r = stats_client.get(
        "/registros", params={"limit": 2, "page": 2}, headers=stats_auth_headers
    )
    data = r.json()
    assert data["total"] == 4
    assert len(data["registros"]) == 2
    assert data["page"] == 2


def test_registros_paginacion_con_filtro(stats_client, stats_auth_headers):
    r = stats_client.get(
        "/registros",
        params={"mes": 1, "limit": 1, "page": 1},
        headers=stats_auth_headers,
    )
    data = r.json()
    assert data["total"] == 2
    assert len(data["registros"]) == 1
    assert data["pages"] == 2
