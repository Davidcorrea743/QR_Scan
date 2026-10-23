import json
import os

import database
import limpiar_uploads


def test_purga_conserva_referenciados_y_borra_huerfanos(client, tmp_path, monkeypatch):
    monkeypatch.setattr(database, "UPLOADS_DIR", str(tmp_path))

    # archivos en disco: 2 referenciados por la BD y 2 huérfanos
    (tmp_path / "empleado_ref.png").write_bytes(b"png")
    (tmp_path / "galeria_ref.png").write_bytes(b"png")
    (tmp_path / "huerfano1.png").write_bytes(b"png")
    (tmp_path / "huerfano2.jpg").write_bytes(b"jpg")

    conn = database.get_connection()
    try:
        conn.execute(
            "INSERT INTO empleados (nombre, apellido, foto) VALUES ('Ana', 'García', 'empleado_ref.png')"
        )
        galeria = json.dumps(["galeria_ref.png"])
        if conn.execute("SELECT id FROM empresa WHERE id = 1").fetchone():
            conn.execute("UPDATE empresa SET galeria = ? WHERE id = 1", (galeria,))
        else:
            conn.execute("INSERT INTO empresa (id, galeria) VALUES (1, ?)", (galeria,))
        conn.commit()
    finally:
        conn.close()

    # dry-run: informa los huérfanos pero no borra nada
    r = limpiar_uploads.purgar_huerfanos(borrar=False)
    assert sorted(r["huerfanos"]) == ["huerfano1.png", "huerfano2.jpg"]
    assert sorted(r["referenciados"]) == ["empleado_ref.png", "galeria_ref.png"]
    assert r["borrados"] == []
    assert (tmp_path / "huerfano1.png").exists()
    assert (tmp_path / "empleado_ref.png").exists()

    # con borrar=True: solo desaparecen los huérfanos
    r = limpiar_uploads.purgar_huerfanos(borrar=True)
    assert sorted(r["borrados"]) == ["huerfano1.png", "huerfano2.jpg"]
    assert not (tmp_path / "huerfano1.png").exists()
    assert not (tmp_path / "huerfano2.jpg").exists()
    assert (tmp_path / "empleado_ref.png").exists()
    assert (tmp_path / "galeria_ref.png").exists()


def test_purga_conserva_foto_de_empleado_inactivo(client, tmp_path, monkeypatch):
    monkeypatch.setattr(database, "UPLOADS_DIR", str(tmp_path))

    (tmp_path / "empleado_inactivo.png").write_bytes(b"png")
    conn = database.get_connection()
    try:
        conn.execute(
            "INSERT INTO empleados (nombre, apellido, foto, activo) "
            "VALUES ('Luis', 'Pérez', 'empleado_inactivo.png', 0)"
        )
        conn.commit()
    finally:
        conn.close()

    r = limpiar_uploads.purgar_huerfanos(borrar=True)
    assert r["huerfanos"] == []
    assert r["borrados"] == []
    assert (tmp_path / "empleado_inactivo.png").exists()
