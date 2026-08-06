import io
import json

from PIL import Image

from tests.test_empleados import DATOS, crear_empleado


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "blue").save(buf, format="PNG")
    return buf.getvalue()


def test_perfil_publico_200(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.get(f"/perfil/{emp_id}")
    assert res.status_code == 200
    body = res.text
    assert "Juan" in body
    assert "Desarrollador" in body
    assert "juan@empresa.com" in body
    assert "3001112233" in body


def test_perfil_no_existe_404(client):
    res = client.get("/perfil/99999")
    assert res.status_code == 404


def test_perfil_inactivo_404(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    client.delete(f"/api/empleados/{emp_id}", headers=auth_headers)
    res = client.get(f"/perfil/{emp_id}")
    assert res.status_code == 404


def test_carnet_pagina(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.get(f"/carnet/{emp_id}")
    assert res.status_code == 200
    assert "Juan" in res.text
    assert "Desarrollador" in res.text


def test_carnet_no_existe_404(client):
    res = client.get("/carnet/99999")
    assert res.status_code == 404


def test_paginas_accesibles(client):
    for ruta in ["/login", "/admin", "/formulario", "/config", "/generador"]:
        res = client.get(ruta)
        assert res.status_code == 200, ruta


def test_escaneo_desde_perfil(client):
    antes = client.get("/registros").json()["total"]
    client.get("/scan")
    despues = client.get("/registros").json()["total"]
    assert despues == antes + 1


def test_config_empresa_requiere_admin(client):
    res = client.get("/api/empresa")
    assert res.status_code == 401


def test_config_empresa_guardar_y_leer(client, auth_headers):
    redes = [{"label": "linkedin", "url": "https://linkedin.com/empresa"}]
    res = client.put(
        "/api/empresa",
        data={
            "nombre": "Empresa Test S.A.S.",
            "redes": json.dumps(redes),
        },
        files={
            "logo": ("logo.png", png_bytes(), "image/png"),
            "fondo": ("fondo.png", png_bytes(), "image/png"),
            "carnet_fondo": ("carnet_fondo.png", png_bytes(), "image/png"),
        },
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text

    res = client.get("/api/empresa", headers=auth_headers)
    data = res.json()
    assert data["nombre"] == "Empresa Test S.A.S."
    assert data["logo"]
    assert data["fondo"]
    assert data["carnet_fondo"]
    assert json.loads(data["redes"]) == redes


def test_carnet_con_fondo_de_empresa(client, auth_headers):
    client.put(
        "/api/empresa",
        data={"nombre": "Empresa Test"},
        files={"carnet_fondo": ("cf.png", png_bytes(), "image/png")},
        headers=auth_headers,
    )
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.get(f"/carnet/{emp_id}")
    assert res.status_code == 200
    assert "url('/uploads/" in res.text


def test_config_empresa_redes_invalidas(client, auth_headers):
    res = client.put(
        "/api/empresa", data={"redes": "no-es-json"}, headers=auth_headers
    )
    assert res.status_code == 400
