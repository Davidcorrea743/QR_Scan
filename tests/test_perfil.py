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


def test_carnet_boton_copiar_url(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/carnet/{emp_id}").text
    assert "Copiar URL" in body
    assert "function copiarURL" in body
    assert f'"/perfil/" + {emp_id}' in body


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
    assert 'class="marco-derecho"' in res.text


def test_carnet_sin_marco_derecho(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/carnet/{emp_id}").text
    assert 'class="marco-derecho"' not in body


def test_carnet_marco_izquierdo(client, auth_headers):
    client.put(
        "/api/empresa",
        data={"nombre": "Empresa Test"},
        files={"fondo": ("marco.png", png_bytes(), "image/png")},
        headers=auth_headers,
    )
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/carnet/{emp_id}").text
    assert 'class="marco-izquierdo"' in body


def test_carnet_sin_marco_izquierdo(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/carnet/{emp_id}").text
    assert 'class="marco-izquierdo"' not in body


def test_config_empresa_redes_invalidas(client, auth_headers):
    res = client.put(
        "/api/empresa", data={"redes": "no-es-json"}, headers=auth_headers
    )
    assert res.status_code == 400


def test_eliminar_imagen_empresa(client, auth_headers):
    client.put(
        "/api/empresa",
        data={"nombre": "Empresa Test"},
        files={
            "logo": ("logo.png", png_bytes(), "image/png"),
            "carnet_fondo": ("cf.png", png_bytes(), "image/png"),
        },
        headers=auth_headers,
    )
    res = client.get("/api/empresa", headers=auth_headers)
    assert res.json()["logo"]
    assert res.json()["carnet_fondo"]

    res = client.delete("/api/empresa/imagen/logo", headers=auth_headers)
    assert res.status_code == 200
    res = client.delete("/api/empresa/imagen/carnet_fondo", headers=auth_headers)
    assert res.status_code == 200

    data = client.get("/api/empresa", headers=auth_headers).json()
    assert not data["logo"]
    assert not data["carnet_fondo"]


def test_eliminar_imagen_campo_invalido(client, auth_headers):
    res = client.delete("/api/empresa/imagen/inexistente", headers=auth_headers)
    assert res.status_code == 400


def test_eliminar_imagen_requiere_admin(client):
    res = client.delete("/api/empresa/imagen/logo")
    assert res.status_code == 401


def test_vcard_descarga(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    client.put("/api/empresa", data={"nombre": "Empresa Test"}, headers=auth_headers)
    res = client.get(f"/vcard/{emp_id}")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/vcard")
    assert "attachment" in res.headers["content-disposition"]
    body = res.text
    assert "BEGIN:VCARD" in body
    assert "END:VCARD" in body
    assert "FN:Juan P\u00e9rez" in body
    assert "ORG:Empresa Test" in body
    assert "TITLE:Desarrollador" in body
    assert "3001112233" in body
    assert "juan@empresa.com" in body


def test_vcard_no_existe_404(client):
    res = client.get("/vcard/99999")
    assert res.status_code == 404


def test_vcard_inactivo_404(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    client.delete(f"/api/empleados/{emp_id}", headers=auth_headers)
    res = client.get(f"/vcard/{emp_id}")
    assert res.status_code == 404


def test_empresa_ubicacion_y_galeria(client, auth_headers):
    res = client.put(
        "/api/empresa",
        data={"nombre": "Empresa Test", "ubicacion": "https://maps.example.com/lugar?a=1&b=2"},
        files=[
            ("galeria", ("g1.png", png_bytes(), "image/png")),
            ("galeria", ("g2.png", png_bytes(), "image/png")),
        ],
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text

    data = client.get("/api/empresa", headers=auth_headers).json()
    assert data["ubicacion"] == "https://maps.example.com/lugar?a=1&b=2"
    galeria = data["galeria"]
    assert isinstance(galeria, list) and len(galeria) == 2

    res = client.delete(f"/api/empresa/galeria/{galeria[0]}", headers=auth_headers)
    assert res.status_code == 200
    data = client.get("/api/empresa", headers=auth_headers).json()
    assert data["galeria"] == [galeria[1]]


def test_perfil_carousel_con_galeria(client, auth_headers):
    client.put(
        "/api/empresa",
        data={"nombre": "Empresa Test"},
        files=[("galeria", ("g.png", png_bytes(), "image/png"))],
        headers=auth_headers,
    )
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/perfil/{emp_id}").text
    assert "carouselEmpresa" in body
    assert "carousel-item active" in body
    assert "img-galeria" in body


def test_perfil_carousel_oculto_sin_galeria(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/perfil/{emp_id}").text
    assert "carouselEmpresa" not in body


def test_perfil_call_center(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/perfil/{emp_id}").text
    assert "Call Center" in body
    assert 'href="tel:+582128195400"' in body
    assert "bi-headset" in body


def test_carnet_trasero_pagina(client, auth_headers):
    client.put(
        "/api/empresa",
        data={
            "nombre": "Empresa Test",
            "trasera_mensaje": "Ante cualquier inquietud, contáctanos.",
            "trasera_correo": "contacto@empresa.com",
            "trasera_telefono": "+58 300 000 0000",
        },
        files={
            "trasera_logo": ("tl.png", png_bytes(), "image/png"),
            "trasera_fondo": ("tf.png", png_bytes(), "image/png"),
        },
        headers=auth_headers,
    )
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.get(f"/carnet/{emp_id}/trasero")
    assert res.status_code == 200
    body = res.text
    assert "Ante cualquier inquietud" in body
    assert "contacto@empresa.com" in body
    assert "+58 300 000 0000" in body
    assert "url('/uploads/" in body
    assert "logo-trasero" in body
    assert "{{" not in body


def test_carnet_trasero_no_existe_404(client):
    res = client.get("/carnet/99999/trasero")
    assert res.status_code == 404


def test_carnet_trasero_rif_por_defecto(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.get(f"/carnet/{emp_id}/trasero")
    assert res.status_code == 200
    assert "RIF: J411377260" in res.text


def test_carnet_trasero_rif_configurable(client, auth_headers):
    client.put(
        "/api/empresa",
        data={"trasera_rif": "J-555555555"},
        headers=auth_headers,
    )
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.get(f"/carnet/{emp_id}/trasero")
    assert res.status_code == 200
    assert "RIF: J-555555555" in res.text


def test_carnet_trasero_rif_guardado_config(client, auth_headers):
    res = client.put(
        "/api/empresa",
        data={"trasera_rif": "J411377260"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = client.get("/api/empresa", headers=auth_headers).json()
    assert data["trasera_rif"] == "J411377260"


def test_carnet_trasero_mensaje_por_defecto(client, auth_headers):
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    res = client.get(f"/carnet/{emp_id}/trasero")
    assert res.status_code == 200
    body = res.text
    assert "Gracias por visitarnos" in body
    assert "{{" not in body


def test_carnet_trasero_nombre_si_sin_logo(client, auth_headers):
    client.put(
        "/api/empresa", data={"nombre": "Empresa Sin Logo"}, headers=auth_headers
    )
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/carnet/{emp_id}/trasero").text
    assert 'class="nombre-trasero">Empresa Sin Logo' in body


def test_carnet_trasero_saltos_de_linea(client, auth_headers):
    client.put(
        "/api/empresa",
        data={
            "trasera_mensaje": (
                "Este carnet es de uso personal e intransferible.\n\n"
                "En caso de extravío, por favor comunicarse:"
            ),
            "trasera_correo": "contacto@empresa.com",
        },
        headers=auth_headers,
    )
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/carnet/{emp_id}/trasero").text
    assert "<br><br>" in body
    assert "Este carnet es de uso personal e intransferible." in body
    assert "En caso de extravío, por favor comunicarse:" in body
    assert "{{" not in body


def test_carnet_trasero_mensaje_escapa_html(client, auth_headers):
    client.put(
        "/api/empresa",
        data={"trasera_mensaje": "Linea uno<br>Linea dos <b>negrita</b>"},
        headers=auth_headers,
    )
    emp_id = crear_empleado(client, auth_headers).json()["id"]
    body = client.get(f"/carnet/{emp_id}/trasero").text
    assert "<br>" in body
    assert "negrita" in body
    assert "<b>negrita</b>" not in body


def test_config_empresa_trasera_guardar_y_borrar(client, auth_headers):
    res = client.put(
        "/api/empresa",
        data={
            "trasera_mensaje": "Mensaje test",
            "trasera_correo": "a@b.com",
            "trasera_telefono": "3000000000",
        },
        files={"trasera_fondo": ("tf.png", png_bytes(), "image/png")},
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text

    data = client.get("/api/empresa", headers=auth_headers).json()
    assert data["trasera_mensaje"] == "Mensaje test"
    assert data["trasera_correo"] == "a@b.com"
    assert data["trasera_telefono"] == "3000000000"
    assert data["trasera_fondo"]

    res = client.delete("/api/empresa/imagen/trasera_fondo", headers=auth_headers)
    assert res.status_code == 200
    data = client.get("/api/empresa", headers=auth_headers).json()
    assert not data["trasera_fondo"]
