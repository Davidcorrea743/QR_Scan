import base64
import io
import json
import os
import urllib.parse
from html import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

import config
import database
import templating

router = APIRouter(tags=["paginas"])

ICONOS_RED = {
    "linkedin": {
        "label": "LinkedIn",
        "path": "M4.98 3.5C4.98 4.78 3.956 5.82 2.577 5.82 1.198 5.82.178 4.78.178 3.5.178 2.22 1.198 1.18 2.577 1.18 3.956 1.18 4.98 2.22 4.98 3.5zM.374 8.25h4.406V24H.374V8.25zM8.08 8.25h4.22v2.16h.06c.588-1.114 2.023-2.29 4.28-2.29 4.577 0 5.423 3.009 5.423 6.92V24h-4.405v-7.96c0-1.897-.034-4.34-2.643-4.34-2.647 0-3.055 2.067-3.055 4.2V24h-4.41V8.25z",
    },
    "twitter": {
        "label": "X (Twitter)",
        "path": "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z",
    },
    "instagram": {
        "label": "Instagram",
        "path": "M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z",
    },
    "facebook": {
        "label": "Facebook",
        "path": "M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z",
    },
    "tiktok": {
        "label": "TikTok",
        "path": "M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z",
    },
    "web": {
        "label": "Sitio web",
        "path": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z",
    },
}


def _empresa_data(conn):
    row = conn.execute("SELECT * FROM empresa WHERE id = 1").fetchone()
    data = dict(row) if row else {}
    try:
        redes = json.loads(data.get("redes") or "[]")
    except (json.JSONDecodeError, TypeError):
        redes = []
    data["redes"] = redes
    try:
        galeria = json.loads(data.get("galeria") or "[]")
    except (json.JSONDecodeError, TypeError):
        galeria = []
    data["galeria"] = galeria
    return data


@router.get("/login", include_in_schema=False)
async def login_page():
    return HTMLResponse(templating.render("login.html"))


@router.get("/admin", include_in_schema=False)
async def admin_page():
    return HTMLResponse(templating.render("admin.html", BASE_URL=config.BASE_URL))


@router.get("/formulario", include_in_schema=False)
async def formulario_page():
    return HTMLResponse(templating.render("formulario.html", BASE_URL=config.BASE_URL))


@router.get("/config", include_in_schema=False)
async def config_page():
    return HTMLResponse(templating.render("config.html", BASE_URL=config.BASE_URL))


@router.get("/generador", include_in_schema=False)
async def generador_page():
    return HTMLResponse(templating.render("generador.html"))


@router.get("/carnet/{emp_id}", include_in_schema=False)
async def carnet_page(emp_id: int):
    conn = database.get_connection()
    try:
        emp = conn.execute(
            "SELECT * FROM empleados WHERE id = ?", (emp_id,)
        ).fetchone()
        empresa = _empresa_data(conn)
    finally:
        conn.close()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    carnet_fondo = empresa.get("carnet_fondo", "")
    carnet_fondo_css = (
        f"url('/uploads/{carnet_fondo}')"
        if carnet_fondo
        else "linear-gradient(135deg, #ffffff, #f4f7fc)"
    )
    logo = empresa.get("titulo") or empresa.get("logo", "")
    if logo:
        empresa_top_html = (
            f'<img class="logo-empresa" src="/uploads/{logo}" alt="Logo de la empresa">'
        )
    else:
        nombre = escape(empresa.get("nombre", ""))
        empresa_top_html = (
            f'<div class="nombre-empresa">{nombre}</div>' if nombre else ""
        )

    return HTMLResponse(
        templating.render(
            "carnet.html",
            BASE_URL=config.BASE_URL,
            EMPRESA_NOMBRE=empresa.get("nombre", ""),
            EMPRESA_LOGO=empresa.get("logo", ""),
            CARNET_FONDO=carnet_fondo,
            CARNET_FONDO_CSS=carnet_fondo_css,
            EMPRESA_TOP_HTML=empresa_top_html,
            EMP_ID=emp["id"],
            NOMBRE=emp["nombre"],
            APELLIDO=emp["apellido"],
            CEDULA=emp["cedula"] or "",
            CARGO=emp["cargo"] or "",
            FOTO=emp["foto"] or "",
        )
    )


@router.get("/vcard/{emp_id}", include_in_schema=False)
async def vcard_trabajador(emp_id: int):
    conn = database.get_connection()
    try:
        emp = conn.execute(
            "SELECT * FROM empleados WHERE id = ? AND activo = 1", (emp_id,)
        ).fetchone()
        empresa = conn.execute("SELECT * FROM empresa WHERE id = 1").fetchone()
    finally:
        conn.close()
    if not emp:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")

    nombre = (emp["nombre"] or "").strip()
    apellido = (emp["apellido"] or "").strip()
    org = (empresa["nombre"] if empresa else None) or ""
    cargo = (emp["cargo"] or "").strip()
    telefono = (emp["telefono"] or "").strip()
    correo = (emp["correo"] or "").strip()

    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{apellido};{nombre};;;"]
    lines.append(f"FN:{nombre} {apellido}".strip())
    if org:
        lines.append(f"ORG:{org}")
    if cargo:
        lines.append(f"TITLE:{cargo}")
    if telefono:
        lines.append(f"TEL;TYPE=CELL:{telefono}")
    if correo:
        lines.append(f"EMAIL;TYPE=WORK:{correo}")
    if emp["foto"]:
        try:
            ruta = os.path.join(database.UPLOADS_DIR, emp["foto"])
            if os.path.exists(ruta):
                from PIL import Image

                img = Image.open(ruta).convert("RGB")
                img.thumbnail((200, 200))
                buf = io.BytesIO()
                img.save(buf, "JPEG")
                lines.append(
                    "PHOTO;ENCODING=b;TYPE=JPEG:"
                    + base64.b64encode(buf.getvalue()).decode()
                )
        except Exception:
            pass
    lines.append("END:VCARD")

    filename = f"{nombre or 'contacto'}_{apellido or emp['id']}.vcf"
    filename = filename.replace(" ", "_")
    filename_ascii = urllib.parse.quote(filename.encode("utf-8"))
    return Response(
        content="\r\n".join(lines),
        media_type="text/vcard",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"contacto.vcf\"; "
                f"filename*=UTF-8''{filename_ascii}"
            )
        },
    )


@router.get("/perfil/{emp_id}", include_in_schema=False)
async def perfil_publico(emp_id: int):
    conn = database.get_connection()
    try:
        emp = conn.execute(
            "SELECT * FROM empleados WHERE id = ? AND activo = 1", (emp_id,)
        ).fetchone()
        empresa = _empresa_data(conn)
    finally:
        conn.close()
    if not emp:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")

    logo = empresa.get("titulo") or empresa.get("logo", "")
    ubicacion = empresa.get("ubicacion", "")
    context = {
        "BASE_URL": config.BASE_URL,
        "EMPRESA_NOMBRE": empresa.get("nombre", ""),
        "EMPRESA_LOGO": logo,
        "NOMBRE": emp["nombre"],
        "APELLIDO": emp["apellido"],
        "CEDULA": emp["cedula"] or "",
        "CARGO": emp["cargo"] or "",
        "CORREO": emp["correo"] or "",
        "TELEFONO": emp["telefono"] or "",
        "FOTO": emp["foto"] or "",
        "REDES": _render_redes(empresa.get("redes", [])),
        "UBICACION": ubicacion,
        "UBICACION_JSON": json.dumps(ubicacion),
        "GALERIA_HTML": _render_galeria(empresa.get("galeria", [])),
        "EMP_ID": emp["id"],
    }
    return HTMLResponse(templating.render("perfil.html", **context))


def _render_galeria(galeria: list) -> str:
    if not galeria:
        return ""
    items = []
    for i, f in enumerate(galeria):
        active = " active" if i == 0 else ""
        items.append(
            f'<div class="carousel-item{active}">'
            f'<img src="/uploads/{f}" class="d-block w-100 img-galeria" '
            f'alt="Imagen {i + 1} de la empresa">'
            f"</div>"
        )
    return (
        '<section class="tarjeta galeria-tarjeta">'
        '<h2 class="titulo-seccion">Nuestra empresa</h2>'
        '<div id="carouselEmpresa" class="carousel slide carousel-dark" '
        'data-bs-ride="carousel" data-bs-interval="4000">'
        '<div class="carousel-inner">' + "".join(items) + "</div>"
        '<button class="carousel-control-prev" type="button" '
        'data-bs-target="#carouselEmpresa" data-bs-slide="prev">'
        '<span class="carousel-control-prev-icon" aria-hidden="true"></span>'
        '<span class="visually-hidden">Anterior</span></button>'
        '<button class="carousel-control-next" type="button" '
        'data-bs-target="#carouselEmpresa" data-bs-slide="next">'
        '<span class="carousel-control-next-icon" aria-hidden="true"></span>'
        '<span class="visually-hidden">Siguiente</span></button>'
        "</div></section>"
    )


def _render_redes(redes: list) -> str:
    links = []
    for r in redes:
        label = (r.get("label") or "").strip().lower()
        url = (r.get("url") or "").strip()
        if not url:
            continue
        icono = ICONOS_RED.get(label)
        if not icono:
            continue
        links.append(
            f'<a class="icono-red" href="{escape(url, quote=True)}" target="_blank" '
            f'rel="noopener" aria-label="{escape(icono["label"])}" title="{escape(icono["label"])}">'
            f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="{icono["path"]}"/></svg></a>'
        )
    return "".join(links)
