import csv
import io
import os
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

import database
import media
from auth import get_current_user, require_admin

router = APIRouter(prefix="/empleados", tags=["empleados"])

CAMPOS_EDITOR = {"telefono", "correo"}

TILDES = str.maketrans(
    "áéíóúüñÁÉÍÓÚÜÑ",
    "aeiouunAEIOUUN",
)

EXT_FOTOS = (".png", ".jpg", ".jpeg", ".webp")
MAX_TAMANO_CSV = 5 * 1024 * 1024
MAX_TAMANO_FOTO = 5 * 1024 * 1024


@router.get("")
def listar(incluir_inactivos: int = 0, user=Depends(get_current_user)):
    conn = database.get_connection()
    try:
        if incluir_inactivos and user["rol"] == "admin":
            rows = conn.execute(
                "SELECT * FROM empleados ORDER BY nombre, apellido"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM empleados WHERE activo = 1 ORDER BY nombre, apellido"
            ).fetchall()
    finally:
        conn.close()
    return {"empleados": [dict(r) for r in rows]}


def _normalizar_clave(clave: str) -> str:
    return (clave or "").strip().lower().translate(TILDES).replace(" ", "_")


def _leer_filas_csv(datos: bytes) -> list:
    try:
        texto = datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = datos.decode("latin-1")
    lineas = texto.splitlines()
    primera = lineas[0] if lineas else ""
    delimitador = ";" if primera.count(";") > primera.count(",") else ","
    return list(csv.DictReader(io.StringIO(texto), delimiter=delimitador))


def _leer_zip_fotos(datos: bytes) -> dict:
    try:
        archivo = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="El archivo de fotos no es un ZIP válido.")
    fotos = {}
    for nombre in archivo.namelist():
        ext = os.path.splitext(nombre)[1].lower()
        if ext not in EXT_FOTOS:
            continue
        if archivo.getinfo(nombre).file_size > MAX_TAMANO_FOTO:
            continue
        fotos[os.path.basename(nombre).lower()] = archivo.read(nombre)
    return fotos


def _buscar_foto(fila: dict, cedula: str, fotos: dict):
    nombre_foto = (fila.get("foto") or "").strip()
    if not nombre_foto and cedula:
        for ext in EXT_FOTOS:
            if (cedula + ext).lower() in fotos:
                nombre_foto = cedula + ext
                break
    if not nombre_foto:
        return None
    datos = fotos.get(os.path.basename(nombre_foto).lower())
    if not datos:
        return None
    try:
        from PIL import Image

        Image.open(io.BytesIO(datos)).verify()
    except Exception:
        return "__invalida__"
    return media.guardar_imagen_bytes(datos, nombre_foto, "empleado")


@router.post("/carga-masiva")
def carga_masiva(
    archivo: UploadFile = File(...),
    zip_fotos: UploadFile = File(None),
    user=Depends(require_admin),
):
    datos = archivo.file.read()
    if len(datos) > MAX_TAMANO_CSV:
        raise HTTPException(status_code=400, detail="El CSV supera el tamaño máximo (5 MB).")
    try:
        filas = _leer_filas_csv(datos)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el CSV.")
    if not filas:
        raise HTTPException(status_code=400, detail="El CSV no tiene datos.")
    filas = [
        {_normalizar_clave(k): v for k, v in fila.items()}
        for fila in filas
        if any((v or "").strip() for v in (fila or {}).values())
    ]
    if not filas:
        raise HTTPException(status_code=400, detail="El CSV no tiene datos.")
    if "nombre" not in filas[0] or "apellido" not in filas[0]:
        raise HTTPException(
            status_code=400,
            detail="El CSV debe tener al menos las columnas 'nombre' y 'apellido'.",
        )
    fotos = _leer_zip_fotos(zip_fotos.file.read()) if zip_fotos else {}

    conn = database.get_connection()
    importados = 0
    omitidos = []
    errores = []
    try:
        existentes = {
            (r["cedula"] or "").strip().lower()
            for r in conn.execute("SELECT cedula FROM empleados").fetchall()
        }
        for i, fila in enumerate(filas, start=2):
            nombre = (fila.get("nombre") or "").strip()
            apellido = (fila.get("apellido") or "").strip()
            cedula = (fila.get("cedula") or "").strip()
            if not nombre or not apellido:
                errores.append({"fila": i, "motivo": "Faltan nombre o apellido."})
                continue
            clave = cedula.lower()
            if clave and clave in existentes:
                omitidos.append(cedula)
                continue
            nombre_foto = _buscar_foto(fila, cedula, fotos)
            if nombre_foto == "__invalida__":
                errores.append({"fila": i, "motivo": "Foto no válida; se creó sin foto."})
                nombre_foto = None
            conn.execute(
                "INSERT INTO empleados (nombre, apellido, cedula, cargo, correo, telefono, foto) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    nombre,
                    apellido,
                    cedula,
                    (fila.get("cargo") or "").strip(),
                    (fila.get("correo") or "").strip(),
                    (fila.get("telefono") or "").strip(),
                    nombre_foto,
                ),
            )
            importados += 1
            if clave:
                existentes.add(clave)
        conn.commit()
    finally:
        conn.close()
    return {"importados": importados, "omitidos": omitidos, "errores": errores}


@router.get("/{emp_id}")
def obtener(emp_id: int, user=Depends(get_current_user)):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return dict(row)


@router.post("")
def crear(
    nombre: str = Form(...),
    apellido: str = Form(...),
    cedula: str = Form(""),
    cargo: str = Form(""),
    correo: str = Form(""),
    telefono: str = Form(""),
    foto: UploadFile = File(None),
    user=Depends(require_admin),
):
    nombre_foto = media.guardar_imagen(foto, "empleado") if foto else None
    conn = database.get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO empleados (nombre, apellido, cedula, cargo, correo, telefono, foto) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                nombre.strip(),
                apellido.strip(),
                cedula.strip(),
                cargo.strip(),
                correo.strip(),
                telefono.strip(),
                nombre_foto,
            ),
        )
        conn.commit()
        emp_id = cur.lastrowid
    finally:
        conn.close()
    return {"id": emp_id}


@router.put("/{emp_id}")
def actualizar(
    emp_id: int,
    nombre: str = Form(None),
    apellido: str = Form(None),
    cedula: str = Form(None),
    cargo: str = Form(None),
    correo: str = Form(None),
    telefono: str = Form(None),
    foto: UploadFile = File(None),
    user=Depends(get_current_user),
):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")

        valores = {}
        if user["rol"] == "admin":
            for k, v in (
                ("nombre", nombre),
                ("apellido", apellido),
                ("cedula", cedula),
                ("cargo", cargo),
                ("correo", correo),
                ("telefono", telefono),
            ):
                if v is not None:
                    valores[k] = v.strip()
        else:
            for k in CAMPOS_EDITOR:
                v = {"telefono": telefono, "correo": correo}[k]
                if v is not None:
                    valores[k] = v.strip()

        if foto:
            nuevo = media.guardar_imagen(foto, "empleado")
            valores["foto"] = nuevo

        if not valores:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")

        sets = ", ".join(f"{k} = ?" for k in valores)
        conn.execute(
            f"UPDATE empleados SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*valores.values(), emp_id),
        )
        conn.commit()
        if foto and row["foto"] and row["foto"] != nuevo:
            media.eliminar_archivo(row["foto"])
    finally:
        conn.close()
    return {"ok": True, "id": emp_id}


@router.delete("/{emp_id}")
def desactivar(emp_id: int, user=Depends(require_admin)):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        conn.execute(
            "UPDATE empleados SET activo = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (emp_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.post("/{emp_id}/restaurar")
def restaurar(emp_id: int, user=Depends(require_admin)):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        conn.execute(
            "UPDATE empleados SET activo = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (emp_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
