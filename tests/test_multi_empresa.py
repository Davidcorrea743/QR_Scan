import database


def _crear_empleado(client, headers, nombre="Ana", apellido="García"):
    return client.post(
        "/api/empleados",
        data={"nombre": nombre, "apellido": apellido, "cedula": "777"},
        headers=headers,
    )


def _crear_usuario_rol(client, headers, username, rol, password="secreto123", empresa_id=None):
    body = {"username": username, "password": password, "rol": rol}
    if empresa_id is not None:
        body["empresa_id"] = empresa_id
    r = client.post("/api/usuarios", json=body, headers=headers)
    assert r.status_code == 200, r.text
    # los usuarios nuevos nacen con debe_cambiar_password=1; lo limpiamos para
    # poder usar el token en los endpoints protegidos
    conn = database.get_connection()
    try:
        conn.execute("UPDATE usuarios SET debe_cambiar_password = 0 WHERE username = ?", (username,))
        conn.commit()
    finally:
        conn.close()
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_esquema_multiempresa(client):
    conn = database.get_connection()
    try:
        sql_empresa = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'empresa'"
        ).fetchone()[0]
        assert "check" not in sql_empresa.lower(), "el CHECK (id = 1) debe eliminarse"

        for tabla in ("empleados", "usuarios", "scans"):
            cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({tabla})")]
            assert "empresa_id" in cols, f"falta empresa_id en {tabla}"
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(scans)")]
        assert "empleado_id" in cols, "falta scans.empleado_id (A3)"

        empresa = conn.execute("SELECT id, nombre FROM empresa WHERE id = 1").fetchone()
        assert empresa is not None
        assert empresa["nombre"], "empresa 1 siempre tiene nombre"
    finally:
        conn.close()


def test_empresa_admite_varias_filas(client):
    conn = database.get_connection()
    try:
        conn.execute("INSERT INTO empresa (id, nombre) VALUES (2, 'Otra empresa')")
        conn.commit()
        n = conn.execute("SELECT COUNT(*) AS n FROM empresa").fetchone()["n"]
        assert n >= 2
    finally:
        conn.close()


def test_migracion_de_roles_admin_a_super_admin(client):
    conn = database.get_connection()
    try:
        conn.execute("UPDATE usuarios SET rol = 'admin'")  # simula BD previa
        conn.commit()
    finally:
        conn.close()

    database.init_database()  # segundo arranque = migración

    conn = database.get_connection()
    try:
        roles = [r["rol"] for r in conn.execute("SELECT rol FROM usuarios")]
    finally:
        conn.close()
    assert roles == ["super_admin"]


def test_admin_creado_despues_de_la_migracion_se_conserva(client, auth_headers):
    _crear_usuario_rol(client, auth_headers, "jefe_rrhh", "admin")

    database.init_database()  # reinicio: no debe tocar los admin ya existentes

    conn = database.get_connection()
    try:
        rol = conn.execute(
            "SELECT rol FROM usuarios WHERE username = 'jefe_rrhh'"
        ).fetchone()["rol"]
    finally:
        conn.close()
    assert rol == "admin"


def test_require_admin_acepta_admin_y_super_admin(client, auth_headers):
    headers_admin = _crear_usuario_rol(client, auth_headers, "admin_emp1", "admin")

    # admin de empresa pasa require_admin...
    assert client.get("/api/empleados", headers=headers_admin).status_code == 200
    # ...y el super_admin (fixture admin) también
    assert client.get("/api/empleados", headers=auth_headers).status_code == 200
    # ...pero un editor no puede crear empleados (acción administrativa)
    headers_editor = _crear_usuario_rol(client, auth_headers, "editor_x", "editor")
    r = client.post(
        "/api/empleados", data={"nombre": "X", "apellido": "Y"}, headers=headers_editor
    )
    assert r.status_code == 403


def test_editor_no_puede_consultar_usuarios(client, auth_headers):
    headers_editor = _crear_usuario_rol(client, auth_headers, "editor_y", "editor")
    assert client.get("/api/usuarios", headers=headers_editor).status_code == 403


def test_scan_vincula_al_empleado_y_empresa(client, auth_headers):
    emp_id = _crear_empleado(client, auth_headers).json()["id"]

    r = client.get(f"/scan?e={emp_id}")
    assert r.status_code == 200

    conn = database.get_connection()
    try:
        scan = conn.execute(
            "SELECT empleado_id, empresa_id FROM scans ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert scan["empleado_id"] == emp_id
    assert scan["empresa_id"] == 1


def test_scan_sin_empleado_valido_queda_sin_vinculo(client, auth_headers):
    client.get("/scan")  # sin parámetro (perfil con HTML antiguo en caché)
    r = client.get("/scan?e=999999")  # empleado inexistente
    assert r.status_code == 200

    conn = database.get_connection()
    try:
        filas = conn.execute(
            "SELECT empleado_id, empresa_id FROM scans ORDER BY id DESC LIMIT 2"
        ).fetchall()
    finally:
        conn.close()
    for fila in filas:
        assert fila["empleado_id"] is None
        assert fila["empresa_id"] == 1


def _crear_empresa2(client, auth_headers, nombre="Empresa 2"):
    r = client.post("/api/empresas", json={"nombre": nombre}, headers=auth_headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_crud_empresas_solo_super_admin(client, auth_headers):
    r = client.get("/api/empresas", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["empresas"]) >= 1

    e2 = _crear_empresa2(client, auth_headers)

    r = client.put(f"/api/empresas/{e2}", json={"nombre": "Empresa 2B"}, headers=auth_headers)
    assert r.status_code == 200

    r = client.put("/api/empresas/99999", json={"nombre": "X"}, headers=auth_headers)
    assert r.status_code == 404

    # un admin común no gestiona empresas
    headers_admin = _crear_usuario_rol(client, auth_headers, "admin_sin_super", "admin")
    assert client.get("/api/empresas", headers=headers_admin).status_code == 403
    r = client.post("/api/empresas", json={"nombre": "Intrusa"}, headers=headers_admin)
    assert r.status_code == 403


def test_aislamiento_empleados_por_empresa(client, auth_headers):
    emp1_id = _crear_empleado(client, auth_headers, "Uno", "Prieto").json()["id"]
    e2 = _crear_empresa2(client, auth_headers)

    # super_admin crea un empleado en la empresa 2
    r = client.post(
        "/api/empleados",
        data={"nombre": "María", "apellido": "López", "cedula": "222", "empresa_id": str(e2)},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    emp2_id = r.json()["id"]
    assert r.json()["empresa_id"] == e2

    h2 = _crear_usuario_rol(client, auth_headers, "admin_e2", "admin", empresa_id=e2)

    # el admin de e2 solo ve a su gente
    r = client.get("/api/empleados", headers=h2)
    assert r.json()["total"] == 1
    assert r.json()["empleados"][0]["id"] == emp2_id

    # y no ve (404, no 403) a un empleado de otra empresa
    assert client.get(f"/api/empleados/{emp1_id}", headers=h2).status_code == 404
    assert client.delete(f"/api/empleados/{emp1_id}", headers=h2).status_code == 404
    assert client.get(f"/api/empleados/{emp2_id}", headers=h2).status_code == 200

    # el super_admin ve todo y puede filtrar por empresa
    r = client.get("/api/empleados", params={"limit": 200}, headers=auth_headers)
    assert r.json()["total"] == 2
    r = client.get("/api/empleados", params={"empresa_id": e2}, headers=auth_headers)
    assert r.json()["total"] == 1
    assert r.json()["empleados"][0]["empresa_id"] == e2

    # el admin de e2 no puede crear en la empresa 1
    r = client.post(
        "/api/empleados",
        data={"nombre": "X", "apellido": "Y", "empresa_id": "1"},
        headers=h2,
    )
    assert r.status_code == 403

    # un editor de e2 no edita empleados de la empresa 1
    editor_h2 = _crear_usuario_rol(client, auth_headers, "editor_e2", "editor", empresa_id=e2)
    r = client.put(
        f"/api/empleados/{emp1_id}", data={"correo": "hack@x.com"}, headers=editor_h2
    )
    assert r.status_code == 404


def test_aislamiento_usuarios(client, auth_headers):
    e2 = _crear_empresa2(client, auth_headers)
    h2 = _crear_usuario_rol(client, auth_headers, "admin_u2", "admin", empresa_id=e2)

    # crea usuarios en su empresa
    r = client.post(
        "/api/usuarios",
        json={"username": "editor_u2", "password": "secreto123", "rol": "editor"},
        headers=h2,
    )
    assert r.status_code == 200

    # ...pero no en otra empresa
    r = client.post(
        "/api/usuarios",
        json={"username": "invasor", "password": "secreto123", "rol": "editor", "empresa_id": 1},
        headers=h2,
    )
    assert r.status_code == 403

    # su lista: solo su empresa y nunca los super_admin
    r = client.get("/api/usuarios", headers=h2)
    nombres = [u["username"] for u in r.json()["usuarios"]]
    assert nombres == ["admin_u2", "editor_u2"]
    assert "admin" not in nombres

    # el super_admin ve a todos
    r = client.get("/api/usuarios", params={"limit": 200}, headers=auth_headers)
    assert "admin" in [u["username"] for u in r.json()["usuarios"]]

    # un admin no gestiona al super_admin (404: ni siquiera sabe que existe)
    conn = database.get_connection()
    try:
        super_id = conn.execute(
            "SELECT id FROM usuarios WHERE username = 'admin'"
        ).fetchone()["id"]
    finally:
        conn.close()
    r = client.put(
        f"/api/usuarios/{super_id}/password",
        json={"password": "robada12345"},
        headers=h2,
    )
    assert r.status_code == 404
    r = client.put(f"/api/usuarios/{super_id}/estado", params={"activo": 0}, headers=h2)
    assert r.status_code == 404


def test_config_empresa_aislada_por_empresa(client, auth_headers):
    e2 = _crear_empresa2(client, auth_headers, nombre="Corp Andina")
    h2 = _crear_usuario_rol(client, auth_headers, "admin_cfg", "admin", empresa_id=e2)

    # super_admin: su empresa por defecto, otra con ?empresa_id=
    assert client.get("/api/empresa", headers=auth_headers).json()["id"] == 1
    assert client.get("/api/empresa", params={"empresa_id": e2}, headers=auth_headers).json()["id"] == e2

    # el admin de e2 escribe solo en la suya
    r = client.put("/api/empresa", data={"nombre": "Mi Co"}, headers=h2)
    assert r.status_code == 200
    assert client.get("/api/empresa", headers=h2).json()["nombre"] == "Mi Co"
    assert client.get("/api/empresa", headers=auth_headers).json()["nombre"] != "Mi Co"

    # intentar escribir en otra empresa → 403
    r = client.put(
        "/api/empresa", data={"nombre": "Hackeada", "empresa_id": "1"}, headers=h2
    )
    assert r.status_code == 403


def test_cedula_unica_por_empresa(client, auth_headers):
    e2 = _crear_empresa2(client, auth_headers)

    # misma cédula en empresas distintas → permitido
    r1 = client.post(
        "/api/empleados",
        data={"nombre": "A", "apellido": "B", "cedula": "999"},
        headers=auth_headers,
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/empleados",
        data={"nombre": "C", "apellido": "D", "cedula": "999", "empresa_id": str(e2)},
        headers=auth_headers,
    )
    assert r2.status_code == 200

    # repetir en la MISMA empresa → 400 (A6)
    r3 = client.post(
        "/api/empleados",
        data={"nombre": "E", "apellido": "F", "cedula": "999"},
        headers=auth_headers,
    )
    assert r3.status_code == 400
    assert "999" in r3.json()["detail"]

    # también en la empresa 2
    r4 = client.post(
        "/api/empleados",
        data={"nombre": "G", "apellido": "H", "cedula": "999", "empresa_id": str(e2)},
        headers=auth_headers,
    )
    assert r4.status_code == 400

    # editar sin cambiar la cédula propia sigue funcionando
    r5 = client.put(
        f"/api/empleados/{r1.json()['id']}",
        data={"cedula": "999", "cargo": "Analista"},
        headers=auth_headers,
    )
    assert r5.status_code == 200


def test_paginas_publicas_usan_empresa_del_empleado(client, auth_headers):
    e2 = _crear_empresa2(client, auth_headers, nombre="Corp Andina")
    emp2 = client.post(
        "/api/empleados",
        data={"nombre": "Pepe", "apellido": "Zamora", "cedula": "333", "empresa_id": str(e2)},
        headers=auth_headers,
    ).json()["id"]

    assert "Corp Andina" in client.get(f"/perfil/{emp2}").text
    assert "Corp Andina" in client.get(f"/carnet/{emp2}").text
    assert "ORG:Corp Andina" in client.get(f"/vcard/{emp2}").text


def test_carga_masiva_respeta_empresa(client, auth_headers):
    e2 = _crear_empresa2(client, auth_headers)
    h2 = _crear_usuario_rol(client, auth_headers, "admin_carga", "admin", empresa_id=e2)

    csv = b"nombre,apellido,cedula\nLuz,Rojas,555\n"
    r = client.post(
        "/api/empleados/carga-masiva",
        files={"archivo": ("e.csv", csv, "text/csv")},
        headers=h2,
    )
    assert r.status_code == 200, r.text
    assert r.json()["importados"] == 1

    r = client.get("/api/empleados", headers=h2)
    assert r.json()["total"] == 1
    assert r.json()["empleados"][0]["empresa_id"] == e2

    # la empresa 1 no contiene ese empleado (aunque el super_admin sí lo lista en general)
    r = client.get(
        "/api/empleados", params={"limit": 200, "empresa_id": 1}, headers=auth_headers
    )
    assert "555" not in [e["cedula"] for e in r.json()["empleados"]]


def test_estadisticas_aisladas_por_empresa(stats_client, stats_auth_headers):
    from datetime import datetime

    import auth as auth_mod

    ahora = datetime.now()
    conn = database.get_connection()
    try:
        conn.execute("INSERT INTO empresa (id, nombre) VALUES (2, 'Empresa 2')")
        conn.execute(
            "INSERT INTO empleados (nombre, apellido, empresa_id) VALUES ('E', 'Dos', 2)"
        )
        emp2 = conn.execute(
            "SELECT id FROM empleados WHERE empresa_id = 2"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO scans (fecha, hora, timestamp, year, month, day, hour, "
            "empresa_id, empleado_id) VALUES (?, ?, ?, ?, ?, ?, ?, 2, ?)",
            (
                ahora.date().isoformat(),
                ahora.time().isoformat(),
                ahora.strftime("%Y-%m-%d %H:%M:%S"),
                ahora.year,
                ahora.month,
                ahora.day,
                ahora.hour,
                emp2,
            ),
        )
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, rol, empresa_id, "
            "debe_cambiar_password, activo) VALUES (?, ?, 'admin', 2, 0, 1)",
            ("admin_stats2", auth_mod.hash_password("secreto123")),
        )
        conn.commit()
    finally:
        conn.close()

    # super_admin: todo (4 sembrados de e1 + 1 de e2)
    r = stats_client.get("/estadisticas", headers=stats_auth_headers)
    assert r.json()["total_escaneos"] == 5
    # ...y puede filtrar por empresa
    r = stats_client.get(
        "/estadisticas", params={"empresa_id": 2}, headers=stats_auth_headers
    )
    assert r.json()["total_escaneos"] == 1

    # el admin de la empresa 2 solo ve lo suyo
    tok = stats_client.post(
        "/api/login", json={"username": "admin_stats2", "password": "secreto123"}
    ).json()["access_token"]
    h2 = {"Authorization": f"Bearer {tok}"}
    r = stats_client.get("/estadisticas", headers=h2)
    assert r.json()["total_escaneos"] == 1
    assert r.json()["escaneos_por_hora_hoy"], "su scan de hoy debe aparecer"

    # registros también aislados
    assert stats_client.get("/registros", headers=h2).json()["total"] == 1
    assert (
        stats_client.get("/registros", headers=stats_auth_headers).json()["total"] == 5
    )
