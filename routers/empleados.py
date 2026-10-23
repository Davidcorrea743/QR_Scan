import csv
import io
import os
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

import database
import media
import rate_limit
from auth import (
    empresa_escrita,
    es_admin,
    es_super_admin,
    exigir_en_alcance,
    get_current_user,
    require_admin,
)
from normalizar import normalizar_correo, normalizar_nombre

router = APIRouter(prefix="/empleados", tags=["empleados"])

TILDES = str.maketrans(
    "áéíóúüñÁÉÍÓÚÜÑ",
    "aeiouunAEIOUUN",
)

EXT_FOTOS = (".png", ".jpg", ".jpeg", ".webp")
MAX_TAMANO_CSV = 5 * 1024 * 1024
MAX_TAMANO_FOTO = 5 * 1024 * 1024
# Límites del ZIP de fotos (QR_MAX_ZIP permite reducirlos en tests).
MAX_TAMANO_ZIP = int(os.environ.get("QR_MAX_ZIP", str(50 * 1024 * 1024)))
MAX_ENTRADAS_ZIP = 5000
MAX_DESComprimido_ZIP = 200 * 1024 * 1024


def _cedula_duplicada(conn, cedula, empresa_id, excluir_id=None) -> bool:
    """A6: cédula única dentro de la misma empresa (ignora vacías)."""
    if not cedula:
        return False
    consulta = (
        "SELECT id FROM empleados WHERE empresa_id = ? AND LOWER(cedula) = LOWER(?)"
    )
    params = [empresa_id, cedula]
    if excluir_id is not None:
        consulta += " AND id != ?"
        params.append(excluir_id)
    return conn.execute(consulta, params).fetchone() is not None


@router.get("")
def listar(
    incluir_inactivos: int = 0,
    page: int = 1,
    limit: int = 10,
    empresa_id: int = None,
    user=Depends(get_current_user),
):
    page = max(1, page)
    limit = max(1, min(limit, 200))
    offset = (page - 1) * limit
    conn = database.get_connection()
    try:
        condiciones = []
        params = []
        puede_ver_inactivos = bool(incluir_inactivos) and es_admin(user)
        if not puede_ver_inactivos:
            condiciones.append("activo = 1")
        if es_super_admin(user):
            # super_admin: todas las empresas (o la que indique con ?empresa_id=)
            if empresa_id is not None:
                condiciones.append("empresa_id = ?")
                params.append(empresa_id)
        else:
            condiciones.append("empresa_id = ?")
            params.append(user["empresa_id"])
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM empleados{where}", params
        ).fetchone()["n"]
        rows = conn.execute(
            f"SELECT * FROM empleados{where} ORDER BY nombre, apellido LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    finally:
        conn.close()
    return {
        "empleados": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
    }


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
    nombres = archivo.namelist()
    if len(nombres) > MAX_ENTRADAS_ZIP:
        raise HTTPException(status_code=400, detail="El ZIP contiene demasiados archivos.")
    fotos = {}
    total_descomprimido = 0
    for nombre in nombres:
        ext = os.path.splitext(nombre)[1].lower()
        if ext not in EXT_FOTOS:
            continue
        info = archivo.getinfo(nombre)
        if info.file_size > MAX_TAMANO_FOTO:
            continue
        total_descomprimido += info.file_size
        if total_descomprimido > MAX_DESComprimido_ZIP:
            raise HTTPException(
                status_code=400, detail="El ZIP de fotos es demasiado grande al descomprimirse."
            )
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
    empresa_id: int = Form(None),
    user=Depends(require_admin),
):
    destino = empresa_escrita(user, empresa_id)
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
    if zip_fotos:
        datos_zip = zip_fotos.file.read(MAX_TAMANO_ZIP + 1)
        if len(datos_zip) > MAX_TAMANO_ZIP:
            raise HTTPException(
                status_code=400,
                detail=f"El ZIP de fotos supera el tamaño máximo ({MAX_TAMANO_ZIP // (1024 * 1024)} MB).",
            )
        fotos = _leer_zip_fotos(datos_zip)
    else:
        fotos = {}

    conn = database.get_connection()
    importados = 0
    omitidos = []
    errores = []
    try:
        existentes = {
            (r["cedula"] or "").strip().lower()
            for r in conn.execute(
                "SELECT cedula FROM empleados WHERE empresa_id = ?", (destino,)
            ).fetchall()
        }
        for i, fila in enumerate(filas, start=2):
            nombre = normalizar_nombre((fila.get("nombre") or "").strip())
            apellido = normalizar_nombre((fila.get("apellido") or "").strip())
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
                "INSERT INTO empleados (nombre, apellido, cedula, cargo, correo, telefono, foto, empresa_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    nombre,
                    apellido,
                    cedula,
                    normalizar_nombre((fila.get("cargo") or "").strip(), conservar_siglas=True),
                    normalizar_correo((fila.get("correo") or "").strip()),
                    (fila.get("telefono") or "").strip(),
                    nombre_foto,
                    destino,
                ),
            )
            importados += 1
            if clave:
                existentes.add(clave)
        conn.commit()
    finally:
        conn.close()
    return {"importados": importados, "omitidos": omitidos, "errores": errores}


@router.get("/carnets/zip")
def descargar_carnets(
    request: Request,
    empresa_id: int = None,
    user=Depends(require_admin),
    _rate=Depends(rate_limit.limitar_zip),
):
    if es_super_admin(user) and empresa_id is not None:
        filtro, params = " AND empresa_id = ?", [empresa_id]
    else:
        filtro, params = " AND empresa_id = ?", [user["empresa_id"]]
    conn = database.get_connection()
    try:
        empleados = conn.execute(
            "SELECT * FROM empleados WHERE activo = 1" + filtro + " ORDER BY apellido, nombre",
            params,
        ).fetchall()
    finally:
        conn.close()
    if not empleados:
        raise HTTPException(status_code=400, detail="No hay empleados activos para descargar.")

    from urllib.parse import urlparse

    from carnets_pdf import generar_zip_carnets

    puerto = urlparse(str(request.base_url)).port or 8000
    base_local = f"http://127.0.0.1:{puerto}"
    try:
        datos = generar_zip_carnets([dict(e) for e in empleados], base_local)
    except Exception as exc:
        print(f"Error generando ZIP de carnets: {exc}")
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudieron generar los PDFs. "
                "Asegúrate de que Chromium esté instalado: "
                "sudo .venv/bin/python -m playwright install-deps chromium."
            ),
        ) from exc
    return StreamingResponse(
        io.BytesIO(datos),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="carnets_frontales.zip"'},
    )


@router.get("/{emp_id}/carnet-pdf")
def generar_carnet_pdf(
    emp_id: int,
    request: Request,
    user=Depends(get_current_user),
    _rate=Depends(rate_limit.limitar_pdf),
):
    conn = database.get_connection()
    try:
        emp = conn.execute(
            "SELECT * FROM empleados WHERE id = ? AND activo = 1", (emp_id,)
        ).fetchone()
    finally:
        conn.close()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    exigir_en_alcance(user, emp["empresa_id"], "Empleado no encontrado")

    from urllib.parse import urlparse

    from carnets_pdf import generar_pdf_carnet, nombre_archivo_pdf

    puerto = urlparse(str(request.base_url)).port or 8000
    base_local = f"http://127.0.0.1:{puerto}"
    try:
        datos = generar_pdf_carnet(dict(emp), base_local)
    except Exception as exc:
        print(f"Error generando PDF para empleado {emp_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="No se pudo generar el PDF. Contacta al administrador.",
        ) from exc
    emp_dict = dict(emp)
    return StreamingResponse(
        io.BytesIO(datos),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_archivo_pdf(emp_dict)}"'
        },
    )


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
    exigir_en_alcance(user, row["empresa_id"], "Empleado no encontrado")
    return dict(row)


@router.post("")
def crear(
    nombre: str = Form(...),
    apellido: str = Form(...),
    cedula: str = Form(""),
    cargo: str = Form(""),
    correo: str = Form(""),
    telefono: str = Form(""),
    empresa_id: int = Form(None),
    foto: UploadFile = File(None),
    user=Depends(require_admin),
):
    destino = empresa_escrita(user, empresa_id)
    nombre_foto = media.guardar_imagen(foto, "empleado") if foto else None
    conn = database.get_connection()
    try:
        # A6: cédula única por empresa
        if _cedula_duplicada(conn, cedula.strip(), destino):
            raise HTTPException(
                status_code=400,
                detail=f"La cédula {cedula.strip()} ya está registrada en esta empresa.",
            )
        cur = conn.execute(
            "INSERT INTO empleados (nombre, apellido, cedula, cargo, correo, telefono, foto, empresa_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                normalizar_nombre(nombre),
                normalizar_nombre(apellido),
                cedula.strip(),
                normalizar_nombre(cargo, conservar_siglas=True),
                normalizar_correo(correo),
                telefono.strip(),
                nombre_foto,
                destino,
            ),
        )
        conn.commit()
        emp_id = cur.lastrowid
    finally:
        conn.close()
    return {"id": emp_id, "empresa_id": destino}


@router.put("/{emp_id}")
def actualizar(
    emp_id: int,
    nombre: str = Form(None),
    apellido: str = Form(None),
    cedula: str = Form(None),
    cargo: str = Form(None),
    correo: str = Form(None),
    telefono: str = Form(None),
    empresa_id: int = Form(None),
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
        exigir_en_alcance(user, row["empresa_id"], "Empleado no encontrado")

        valores = {}
        nuevo = None
        if es_admin(user):
            if nombre is not None:
                valores["nombre"] = normalizar_nombre(nombre)
            if apellido is not None:
                valores["apellido"] = normalizar_nombre(apellido)
            if cedula is not None:
                # A6: cédula única por empresa
                if _cedula_duplicada(conn, cedula.strip(), row["empresa_id"], excluir_id=emp_id):
                    raise HTTPException(
                        status_code=400,
                        detail=f"La cédula {cedula.strip()} ya está registrada en esta empresa.",
                    )
                valores["cedula"] = cedula.strip()
            if cargo is not None:
                valores["cargo"] = normalizar_nombre(cargo, conservar_siglas=True)
            if correo is not None:
                valores["correo"] = normalizar_correo(correo)
            if telefono is not None:
                valores["telefono"] = telefono.strip()
            if foto:
                nuevo = media.guardar_imagen(foto, "empleado")
                valores["foto"] = nuevo
            # solo super_admin puede mover el empleado a otra empresa
            if empresa_id is not None and empresa_id != row["empresa_id"]:
                if not es_super_admin(user):
                    raise HTTPException(
                        status_code=403, detail="No puedes mover empleados a otra empresa"
                    )
                destino = empresa_escrita(user, empresa_id)
                valores["empresa_id"] = destino
        else:
            if foto:
                raise HTTPException(
                    status_code=400,
                    detail="Solo un administrador puede cambiar la foto",
                )
            if correo is not None:
                valores["correo"] = normalizar_correo(correo)
            if telefono is not None:
                valores["telefono"] = telefono.strip()

        if not valores:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")

        sets = ", ".join(f"{k} = ?" for k in valores)
        conn.execute(
            f"UPDATE empleados SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*valores.values(), emp_id),
        )
        conn.commit()
        if nuevo and row["foto"] and row["foto"] != nuevo:
            media.eliminar_archivo(row["foto"])
    finally:
        conn.close()
    return {"ok": True, "id": emp_id}


@router.delete("/{emp_id}")
def desactivar(emp_id: int, user=Depends(require_admin)):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT id, empresa_id FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        exigir_en_alcance(user, row["empresa_id"], "Empleado no encontrado")
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
            "SELECT id, empresa_id FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        exigir_en_alcance(user, row["empresa_id"], "Empleado no encontrado")
        conn.execute(
            "UPDATE empleados SET activo = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (emp_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
