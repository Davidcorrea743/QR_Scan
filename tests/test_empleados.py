import io
import os
import zipfile

from PIL import Image

import database
from carnets_pdf import nombre_archivo_pdf
from normalizar import normalizar_correo, normalizar_nombre

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
    assert emp["cargo"] == "Líder Técnico"
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


def zip_con_fotos(**fotos):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for nombre, datos in fotos.items():
            z.writestr(nombre, datos)
    return buf.getvalue()


def post_csv(client, headers, texto, zip_bytes=None):
    files = {"archivo": ("data.csv", texto.encode("utf-8"), "text/csv")}
    if zip_bytes is not None:
        files["zip_fotos"] = ("fotos.zip", zip_bytes, "application/zip")
    return client.post("/api/empleados/carga-masiva", files=files, headers=headers)


def test_carga_masiva_basica(client, auth_headers):
    csv_texto = (
        "nombre,apellido,cargo,cedula,telefono,correo\n"
        "Ana,López,Analista,123,111,ana@x.com\n"
        "Luis,García,Técnico,456,222,luis@x.com\n"
    )
    res = post_csv(client, auth_headers, csv_texto)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["importados"] == 2
    assert data["omitidos"] == []
    assert data["errores"] == []

    empleados = client.get("/api/empleados", headers=auth_headers).json()["empleados"]
    assert len(empleados) == 2
    assert empleados[0]["correo"] == "ana@x.com"


def test_carga_masiva_fila_invalida(client, auth_headers):
    csv_texto = "nombre,apellido\nAna,López\n, García\n"
    res = post_csv(client, auth_headers, csv_texto)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["importados"] == 1
    assert data["errores"] == [{"fila": 3, "motivo": "Faltan nombre o apellido."}]


def test_carga_masiva_cedula_duplicada_se_omite(client, auth_headers):
    crear_empleado(client, auth_headers)
    csv_texto = "nombre,apellido,cedula\nAna,López,1090123456\nLuis,García,777\n"
    res = post_csv(client, auth_headers, csv_texto)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["importados"] == 1
    assert data["omitidos"] == ["1090123456"]
    assert data["errores"] == []


def test_carga_masiva_separador_punto_coma(client, auth_headers):
    csv_texto = "nombre;apellido;cedula\nAna;López;123\n"
    res = post_csv(client, auth_headers, csv_texto)
    assert res.status_code == 200, res.text
    assert res.json()["importados"] == 1


def test_carga_masiva_encabezados_con_tildes(client, auth_headers):
    csv_texto = "Nombre;Apellido;Cédula\nAna;López;123\n"
    res = post_csv(client, auth_headers, csv_texto)
    assert res.status_code == 200, res.text
    assert res.json()["importados"] == 1


def test_carga_masiva_foto_por_cedula(client, auth_headers):
    csv_texto = "nombre,apellido,cedula\nAna,López,12345678\n"
    res = post_csv(client, auth_headers, csv_texto, zip_con_fotos(**{"12345678.jpg": png_bytes()}))
    assert res.status_code == 200, res.text
    assert res.json()["importados"] == 1

    emp = client.get("/api/empleados", headers=auth_headers).json()["empleados"][0]
    assert emp["foto"]
    assert os.path.exists(os.path.join(database.UPLOADS_DIR, emp["foto"]))


def test_carga_masiva_foto_por_columna(client, auth_headers):
    csv_texto = "nombre,apellido,cedula,foto\nAna,López,12345678,ana.jpg\n"
    res = post_csv(client, auth_headers, csv_texto, zip_con_fotos(**{"ana.jpg": png_bytes()}))
    assert res.status_code == 200, res.text
    assert res.json()["importados"] == 1
    emp = client.get("/api/empleados", headers=auth_headers).json()["empleados"][0]
    assert emp["foto"]


def test_carga_masiva_foto_invalida_no_bloquea(client, auth_headers):
    csv_texto = "nombre,apellido,cedula\nAna,López,12345678\n"
    res = post_csv(
        client, auth_headers, csv_texto, zip_con_fotos(**{"12345678.jpg": b"no es imagen"})
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["importados"] == 1
    assert data["errores"][0]["motivo"] == "Foto no válida; se creó sin foto."
    emp = client.get("/api/empleados", headers=auth_headers).json()["empleados"][0]
    assert not emp["foto"]


def test_carga_masiva_sin_encabezados_obligatorios(client, auth_headers):
    res = post_csv(client, auth_headers, "solo,nombre\n1,2\n")
    assert res.status_code == 400


def test_carga_masiva_zip_invalido(client, auth_headers):
    csv_texto = "nombre,apellido\nAna,López\n"
    res = post_csv(client, auth_headers, csv_texto, b"esto no es un zip")
    assert res.status_code == 400


def test_carga_masiva_editor_no_puede(client, auth_headers):
    tok = token_editor(client, auth_headers)
    h = {"Authorization": f"Bearer {tok}"}
    res = post_csv(client, h, "nombre,apellido\nAna,López\n")
    assert res.status_code == 403


def test_carga_masiva_sin_auth(client):
    res = post_csv(client, {}, "nombre,apellido\nAna,López\n")
    assert res.status_code == 401


def test_normalizar_nombre():
    assert normalizar_nombre("pEpITO PereZ") == "Pepito Perez"
    assert normalizar_nombre("  MARIA   DE LOS ANGELES  ") == "Maria de los Angeles"
    assert normalizar_nombre("PÉREZ") == "Pérez"
    assert normalizar_nombre("JUAN CARLOS") == "Juan Carlos"
    assert normalizar_nombre("") == ""
    assert normalizar_nombre("   ") == ""


def test_normalizar_cargo_con_siglas():
    assert normalizar_nombre("desaRROLLAdoR") == "Desarrollador"
    assert normalizar_nombre("JEFE DE RRHH", conservar_siglas=True) == "Jefe de Rrhh"
    assert normalizar_nombre("Desarrollador RRHH", conservar_siglas=True) == "Desarrollador RRHH"
    assert normalizar_nombre("ANALISTA DE SISTEMAS", conservar_siglas=True) == "Analista de Sistemas"


def test_normalizar_correo():
    assert normalizar_correo("JUAN@Empresa.com") == "juan@empresa.com"
    assert normalizar_correo("  A@B.com  ") == "a@b.com"


def test_crear_empleado_normaliza_datos(client, auth_headers):
    res = client.post(
        "/api/empleados",
        data={
            "nombre": "pEpITO",
            "apellido": "PereZ",
            "cedula": "V-123",
            "cargo": "desaRROLLAdoR",
            "correo": "JUAN@Empresa.com",
            "telefono": "  +58 000  ",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text
    emp = client.get("/api/empleados", headers=auth_headers).json()["empleados"][0]
    assert emp["nombre"] == "Pepito"
    assert emp["apellido"] == "Perez"
    assert emp["cargo"] == "Desarrollador"
    assert emp["correo"] == "juan@empresa.com"


def test_actualizar_normaliza_datos(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.put(
        f"/api/empleados/{emp_id}",
        data={"cargo": "JEFE DE RRHH", "correo": "NUEVO@Empresa.com"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    emp = client.get(f"/api/empleados/{emp_id}", headers=auth_headers).json()
    assert emp["cargo"] == "Jefe de Rrhh"
    assert emp["correo"] == "nuevo@empresa.com"


def test_carga_masiva_normaliza_datos(client, auth_headers):
    csv_texto = "nombre,apellido,cargo,cedula,correo\npEpITO,PereZ,desaRROLLAdoR,123,JUAN@Empresa.com\n"
    res = post_csv(client, auth_headers, csv_texto)
    assert res.status_code == 200, res.text
    assert res.json()["importados"] == 1
    emp = client.get("/api/empleados", headers=auth_headers).json()["empleados"][0]
    assert emp["nombre"] == "Pepito"
    assert emp["apellido"] == "Perez"
    assert emp["cargo"] == "Desarrollador"
    assert emp["correo"] == "juan@empresa.com"


def test_normalizacion_datos_existentes(client):
    conn = database.get_connection()
    conn.execute(
        "INSERT INTO empleados (nombre, apellido, cargo, correo) VALUES (?, ?, ?, ?)",
        ("pEpITO", "PereZ", "desaRROLLAdoR", "JUAN@Empresa.com"),
    )
    conn.commit()
    conn.close()

    database.init_database()

    conn = database.get_connection()
    row = conn.execute("SELECT * FROM empleados").fetchone()
    conn.close()
    assert row["nombre"] == "Pepito"
    assert row["apellido"] == "Perez"
    assert row["cargo"] == "Desarrollador"
    assert row["correo"] == "juan@empresa.com"


def test_nombre_archivo_pdf():
    assert nombre_archivo_pdf({"id": 5, "nombre": "Juan", "apellido": "Pérez", "cedula": "123"}) == "Pérez_Juan_123.pdf"
    assert nombre_archivo_pdf({"id": 5, "nombre": "  Ana", "apellido": "De Los Ríos", "cedula": ""}) == "De_Los_Ríos_Ana_5.pdf"
    assert nombre_archivo_pdf({"id": 5, "nombre": "Juan", "apellido": "", "cedula": "A:1"}) == "sin_apellido_Juan_A1.pdf"


def test_descargar_carnets_zip_solo_activos(client, auth_headers, monkeypatch):
    crear_empleado(client, auth_headers)
    emp2 = client.post(
        "/api/empleados",
        data={**DATOS, "nombre": "Luis", "cedula": "777"},
        headers=auth_headers,
    ).json()["id"]
    client.delete(f"/api/empleados/{emp2}", headers=auth_headers)

    def fake_generar(empleados, base_url):
        assert len(empleados) == 1
        assert empleados[0]["cedula"] == "1090123456"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for e in empleados:
                z.writestr(nombre_archivo_pdf(e), b"%PDF-fake")
        return buf.getvalue()

    monkeypatch.setattr("carnets_pdf.generar_zip_carnets", fake_generar)
    res = client.get("/api/empleados/carnets/zip", headers=auth_headers)
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        assert zf.namelist() == ["Pérez_Juan_1090123456.pdf"]


def test_descargar_carnets_zip_requiere_admin(client, auth_headers):
    tok = token_editor(client, auth_headers)
    res = client.get(
        "/api/empleados/carnets/zip", headers={"Authorization": f"Bearer {tok}"}
    )
    assert res.status_code == 403
    res = client.get("/api/empleados/carnets/zip")
    assert res.status_code == 401


def test_descargar_carnets_zip_sin_empleados(client, auth_headers):
    res = client.get("/api/empleados/carnets/zip", headers=auth_headers)
    assert res.status_code == 400


def test_descargar_carnets_zip_error_claro(client, auth_headers, monkeypatch):
    crear_empleado(client, auth_headers)

    def explota(empleados, base_url):
        raise RuntimeError("BrowserType.launch: libnspr4.so")

    monkeypatch.setattr("carnets_pdf.generar_zip_carnets", explota)
    res = client.get("/api/empleados/carnets/zip", headers=auth_headers)
    assert res.status_code == 500
    assert "playwright install-deps" in res.json()["detail"]
