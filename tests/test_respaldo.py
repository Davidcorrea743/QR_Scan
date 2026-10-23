import os

import database
import respaldar


def test_respaldo_copia_todas_las_tablas(empty_client, tmp_path):
    destino = str(tmp_path / "backup.db")
    ruta = respaldar.respaldar(destino=destino)

    assert os.path.exists(ruta)
    origen = respaldar.conteos(database.DB_PATH)
    copia = respaldar.conteos(ruta)
    assert copia == origen
    assert origen["usuarios"] >= 1  # el admin sembrado

    # la BD de origen sigue intacta
    assert os.path.exists(database.DB_PATH)
    assert respaldar.conteos(database.DB_PATH) == origen


def test_respaldo_por_defecto_en_carpeta_respaldos(empty_client, monkeypatch, tmp_path):
    monkeypatch.setattr(database, "BASE_DIR", str(tmp_path))
    ruta = respaldar.respaldar()

    assert ruta.startswith(str(tmp_path))
    assert os.path.basename(ruta).startswith("qr_tracker_")
    assert ruta.endswith(".db")
    assert os.path.exists(ruta)

    # dos respaldos en el mismo instante no se pisan
    ruta2 = respaldar.respaldar()
    assert ruta2 != ruta
    assert os.path.exists(ruta2)
