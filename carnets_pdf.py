import asyncio
import io
import re
import zipfile

INVALIDOS = re.compile(r'[\\/:*?"<>|\r\n\t]')
PARALELISMO = 5


def nombre_archivo_pdf(emp) -> str:
    apellido = (emp.get("apellido") or "").strip() or "sin_apellido"
    nombre = (emp.get("nombre") or "").strip() or "sin_nombre"
    cedula = (emp.get("cedula") or "").strip()
    partes = [p for p in (apellido, nombre, cedula) if p]
    if not cedula:
        partes.append(str(emp["id"]))
    base = INVALIDOS.sub("", "_".join(partes)).replace(" ", "_")
    return f"{base}.pdf"


def generar_zip_carnets(empleados, base_url) -> bytes:
    """Genera un ZIP en memoria con un PDF de 2 páginas por empleado activo.

    Usa Chromium headless (Playwright) navegando a /carnet/{id} (frontal) y
    /carnet/{id}/trasero (reverso), y une ambas caras en un solo PDF con
    pypdf. Paralelismo para acelerar.
    """
    from pypdf import PdfWriter
    from playwright.async_api import async_playwright

    async def _trabajo():
        buffer = io.BytesIO()
        usados = set()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                try:
                    semaforo = asyncio.Semaphore(PARALELISMO)

                    async def procesar(emp):
                        async with semaforo:
                            pagina = await browser.new_page()
                            try:
                                base = base_url.rstrip("/")
                                caras = (
                                    f"/carnet/{emp['id']}",
                                    f"/carnet/{emp['id']}/trasero",
                                )
                                pdfs = []
                                for ruta in caras:
                                    await pagina.goto(
                                        base + ruta, wait_until="load", timeout=60000
                                    )
                                    pdfs.append(
                                        await pagina.pdf(
                                            prefer_css_page_size=True,
                                            print_background=True,
                                        )
                                    )
                            finally:
                                await pagina.close()
                        escritor = PdfWriter()
                        for datos in pdfs:
                            escritor.append(io.BytesIO(datos))
                        salida = io.BytesIO()
                        escritor.write(salida)
                        nombre = nombre_archivo_pdf(emp)
                        if nombre in usados:
                            nombre = f"{nombre[:-4]}_{emp['id']}.pdf"
                        usados.add(nombre)
                        zf.writestr(nombre, salida.getvalue())

                    await asyncio.gather(*(procesar(e) for e in empleados))
                finally:
                    await browser.close()
        return buffer.getvalue()

    return asyncio.run(_trabajo())


def generar_pdf_carnet(emp, base_url) -> bytes:
    """Genera un PDF de 2 páginas (frontal + trasero) para un solo empleado.

    Navega a /carnet/{id} y /carnet/{id}/trasero con Chromium headless,
    y une ambas caras en un solo PDF con pypdf.
    """
    from pypdf import PdfWriter
    from playwright.async_api import async_playwright

    async def _trabajo():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                pagina = await browser.new_page()
                try:
                    base = base_url.rstrip("/")
                    caras = (
                        f"/carnet/{emp['id']}",
                        f"/carnet/{emp['id']}/trasero",
                    )
                    pdfs = []
                    for ruta in caras:
                        await pagina.goto(
                            base + ruta, wait_until="load", timeout=60000
                        )
                        pdfs.append(
                            await pagina.pdf(
                                prefer_css_page_size=True,
                                print_background=True,
                            )
                        )
                finally:
                    await pagina.close()
            finally:
                await browser.close()
        escritor = PdfWriter()
        for datos in pdfs:
            escritor.append(io.BytesIO(datos))
        salida = io.BytesIO()
        escritor.write(salida)
        return salida.getvalue()

    return asyncio.run(_trabajo())
