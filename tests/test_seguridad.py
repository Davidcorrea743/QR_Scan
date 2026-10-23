import os

import database
import media


def _png_invalido():
    return b"esto no es una imagen real"


# --- Política de contraseñas (mínimo 8) ---


def test_password_corta_rechazada(client, auth_headers):
    res = client.post(
        "/api/usuarios",
        json={"username": "corto", "password": "1234567", "rol": "editor"},
        headers=auth_headers,
    )
    assert res.status_code == 400
    assert "8" in res.json()["detail"]


def test_password_de_8_aceptada(client, auth_headers):
    res = client.post(
        "/api/usuarios",
        json={"username": "bien", "password": "12345678", "rol": "editor"},
        headers=auth_headers,
    )
    assert res.status_code == 200


def test_cambio_password_corta_rechazado(client):
    token = client.post(
        "/api/login", json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    res = client.post(
        "/api/password",
        json={"password_actual": "admin123", "password_nueva": "corta"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


# --- debe_cambiar_password forzado en backend ---


def test_debe_cambiar_password_bloquea_api(client):
    token = client.post(
        "/api/login", json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # /api/me y /api/password siguen permitidos
    assert client.get("/api/me", headers=h).status_code == 200

    # Cualquier otro endpoint queda bloqueado hasta cambiar la clave
    assert client.get("/api/usuarios", headers=h).status_code == 403

    # Tras cambiar la clave, la API queda desbloqueada
    res = client.post(
        "/api/password",
        json={"password_actual": "admin123", "password_nueva": "nuevaclv1"},
        headers=h,
    )
    assert res.status_code == 200
    assert client.get("/api/usuarios", headers=h).status_code == 200


# --- carnet-pdf exige token ---


def test_carnet_pdf_requiere_token(client, auth_headers):
    emp_id = client.post(
        "/api/empleados", data={"nombre": "Ana", "apellido": "García"}, headers=auth_headers
    ).json()["id"]
    # Sin token → 401
    assert client.get(f"/api/empleados/{emp_id}/carnet-pdf").status_code == 401


# --- rate limit de login ---


def test_login_rate_limit(client):
    for _ in range(10):
        client.post("/api/login", json={"username": "admin", "password": "mal"})
    res = client.post("/api/login", json={"username": "admin", "password": "mal"})
    assert res.status_code == 429


# --- media: anti path-traversal y validación ---


def test_media_no_escapa_uploads():
    fuera = os.path.join(database.BASE_DIR, "no_deberia_borrarse.txt")
    with open(fuera, "w") as f:
        f.write("hola")
    try:
        for nombre in (
            "../no_deberia_borrarse.txt",
            "..\\no_deberia_borrarse.txt",
            "../../etc/passwd",
            "/etc/passwd",
        ):
            media.eliminar_archivo(nombre)
        assert os.path.exists(fuera)
    finally:
        if os.path.exists(fuera):
            os.remove(fuera)


def test_subida_imagen_invalida_rechazada(client, auth_headers):
    res = client.post(
        "/api/empleados",
        data={"nombre": "Test", "apellido": "Foto"},
        files={"foto": ("foto.png", _png_invalido(), "image/png")},
        headers=auth_headers,
    )
    assert res.status_code == 400


# --- dashboard 8001 exige token ---


def test_dashboard_8001_requiere_token(stats_client):
    assert stats_client.get("/registros").status_code == 401
    assert stats_client.get("/estadisticas").status_code == 401


def test_dashboard_8001_login_y_acceso(stats_client):
    r = stats_client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_dashboard_8001_login_rate_limit(stats_client):
    for _ in range(10):
        stats_client.post("/api/login", json={"username": "admin", "password": "mal"})
    r = stats_client.post("/api/login", json={"username": "admin", "password": "mal"})
    assert r.status_code == 429


# --- CORS y headers de seguridad ---


def test_sin_cors_allow_origin(client):
    r = client.get("/api/me", headers={"Origin": "http://evil.com"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_security_headers(client):
    r = client.get("/login")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# --- SECRET_KEY sin default predecible ---


def test_secret_key_no_es_la_de_siempre():
    import auth

    assert auth.SECRET_KEY != "carnet-qr-secret-cambiar-en-produccion"
    assert len(auth.SECRET_KEY) >= 32
