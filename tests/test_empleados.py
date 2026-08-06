import io

from PIL import Image

DATOS = {
    "nombre": "Juan",
    "apellido": "Pérez",
    "cedula": "1090123456",
    "cargo": "Desarrollador",
    "correo": "juan@empresa.com",
    "telefono": "3001112233",
}


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(buf, format="PNG")
    return buf.getvalue()


def crear_empleado(client, headers, **extra):
    data = dict(DATOS)
    data.update(extra)
    files = {"foto": ("foto.png", png_bytes(), "image/png")}
    return client.post("/api/empleados", data=data, files=files, headers=headers)


def token_editor(client, auth_headers):
    client.post(
        "/api/usuarios",
        json={"username": "editor", "password": "clave123", "rol": "editor"},
        headers=auth_headers,
    )
    return client.post(
        "/api/login", json={"username": "editor", "password": "clave123"}
    ).json()["access_token"]


def test_crear_empleado(client, auth_headers):
    res = crear_empleado(client, auth_headers)
    assert res.status_code == 200, res.text
    emp_id = res.json()["id"]

    res = client.get("/api/empleados", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["empleados"][0]["id"] == emp_id
    assert res.json()["empleados"][0]["nombre"] == "Juan"


def test_crear_empleado_sin_foto(client, auth_headers):
    res = client.post("/api/empleados", data=DATOS, headers=auth_headers)
    assert res.status_code == 200, res.text


def test_crear_empleado_sin_auth(client):
    res = client.post("/api/empleados", data=DATOS)
    assert res.status_code == 401


def test_editor_no_puede_crear(client, auth_headers):
    tok = token_editor(client, auth_headers)
    res = client.post(
        "/api/empleados", data=DATOS, headers={"Authorization": f"Bearer {tok}"}
    )
    assert res.status_code == 403


def test_editor_solo_edita_telefono_y_correo(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    tok = token_editor(client, auth_headers)
    h = {"Authorization": f"Bearer {tok}"}

    res = client.put(
        f"/api/empleados/{emp_id}",
        data={
            "nombre": "HACK",
            "apellido": "HACK",
            "cedula": "111",
            "cargo": "HACK",
            "correo": "nuevo@empresa.com",
            "telefono": "999888777",
        },
        headers=h,
    )
    assert res.status_code == 200

    emp = client.get(f"/api/empleados/{emp_id}", headers=auth_headers).json()
    assert emp["correo"] == "nuevo@empresa.com"
    assert emp["telefono"] == "999888777"
    assert emp["nombre"] == "Juan"
    assert emp["apellido"] == "Pérez"
    assert emp["cedula"] == "1090123456"
    assert emp["cargo"] == "Desarrollador"


def test_admin_edita_todos_los_campos(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.put(
        f"/api/empleados/{emp_id}",
        data={"cargo": "Líder técnico", "cedula": "777777"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    emp = client.get(f"/api/empleados/{emp_id}", headers=auth_headers).json()
    assert emp["cargo"] == "Líder técnico"
    assert emp["cedula"] == "777777"


def test_soft_delete_y_restaurar(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]

    res = client.delete(f"/api/empleados/{emp_id}", headers=auth_headers)
    assert res.status_code == 200

    res = client.get("/api/empleados", headers=auth_headers)
    assert res.json()["empleados"] == []

    res = client.get("/api/empleados?incluir_inactivos=1", headers=auth_headers)
    assert res.json()["empleados"][0]["activo"] == 0

    res = client.post(f"/api/empleados/{emp_id}/restaurar", headers=auth_headers)
    assert res.status_code == 200

    res = client.get("/api/empleados", headers=auth_headers)
    assert res.json()["empleados"][0]["activo"] == 1


def test_empleado_no_existe_404(client, auth_headers):
    res = client.get("/api/empleados/99999", headers=auth_headers)
    assert res.status_code == 404
    res = client.put("/api/empleados/99999", data={"telefono": "1"}, headers=auth_headers)
    assert res.status_code == 404
