def test_login_admin_inicial(client):
    res = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert data["rol"] == "admin"
    assert data["debe_cambiar_password"] == 1
    assert data["access_token"]


def test_login_incorrecto(client):
    res = client.post("/api/login", json={"username": "admin", "password": "mal"})
    assert res.status_code == 401


def test_login_sin_credenciales(client):
    res = client.post("/api/login", json={})
    assert res.status_code == 422


def test_me_sin_token(client):
    res = client.get("/api/me")
    assert res.status_code == 401


def test_me_con_token(client, auth_headers):
    res = client.get("/api/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["username"] == "admin"


def test_me_token_invalido(client):
    res = client.get("/api/me", headers={"Authorization": "Bearer abc"})
    assert res.status_code == 401


def test_cambio_password_obligatorio(client):
    res = client.post(
        "/api/password",
        json={"password_actual": "admin123", "password_nueva": "nueva123"},
        headers={
            "Authorization": f"Bearer {client.post('/api/login', json={'username': 'admin', 'password': 'admin123'}).json()['access_token']}"
        },
    )
    assert res.status_code == 200
    res = client.post("/api/login", json={"username": "admin", "password": "nueva123"})
    assert res.status_code == 200
    assert res.json()["debe_cambiar_password"] == 0


def test_cambio_password_actual_incorrecta(client, auth_headers):
    res = client.post(
        "/api/password",
        json={"password_actual": "incorrecta", "password_nueva": "nueva123"},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_crear_editor_y_login(client, auth_headers):
    res = client.post(
        "/api/usuarios",
        json={"username": "rh1", "password": "clave123", "rol": "editor"},
        headers=auth_headers,
    )
    assert res.status_code == 200

    res = client.post("/api/login", json={"username": "rh1", "password": "clave123"})
    assert res.status_code == 200
    assert res.json()["rol"] == "editor"


def test_crear_usuario_duplicado(client, auth_headers):
    client.post(
        "/api/usuarios",
        json={"username": "dup", "password": "clave123", "rol": "editor"},
        headers=auth_headers,
    )
    res = client.post(
        "/api/usuarios",
        json={"username": "dup", "password": "clave123", "rol": "editor"},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_editor_no_crea_usuarios(client, auth_headers):
    client.post(
        "/api/usuarios",
        json={"username": "editor1", "password": "clave123", "rol": "editor"},
        headers=auth_headers,
    )
    token = client.post(
        "/api/login", json={"username": "editor1", "password": "clave123"}
    ).json()["access_token"]
    res = client.post(
        "/api/usuarios",
        json={"username": "x", "password": "clave123", "rol": "editor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_listar_usuarios(client, auth_headers):
    res = client.get("/api/usuarios", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["usuarios"][0]["username"] == "admin"
