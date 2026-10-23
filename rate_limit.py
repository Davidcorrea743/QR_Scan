"""Limitador de peticiones en memoria (ventana deslizante por IP).

Sin dependencias externas. Funciona bien con un solo proceso uvicorn (que es
como corre este proyecto). El estado se pierde al reiniciar el servidor.
"""

import os
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

# Límites por minuto, configurables por entorno.
LIMITE_SCAN = int(os.environ.get("QR_RATE_LIMIT_SCAN", "30"))
LIMITE_LOGIN = int(os.environ.get("QR_RATE_LIMIT_LOGIN", "10"))
LIMITE_PDF = int(os.environ.get("QR_RATE_LIMIT_PDF", "20"))
LIMITE_ZIP = int(os.environ.get("QR_RATE_LIMIT_ZIP", "10"))
VENTANA_SEGUNDOS = 60

_HABILITADO = os.environ.get("QR_RATE_LIMIT", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)

_bloqueo = threading.Lock()
_baldes = defaultdict(list)  # clave -> [timestamp, ...]


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


def _podar(ahora: float) -> None:
    """Elimina claves inactivas para no crecer sin límite (con el lock tomado)."""
    if len(_baldes) < 10_000:
        return
    for clave in list(_baldes):
        tiempos = _baldes[clave]
        if not tiempos or ahora - tiempos[-1] >= VENTANA_SEGUNDOS:
            del _baldes[clave]


def registrado(clave: str, max_peticiones: int) -> bool:
    """Devuelve True si la petición está permitida y la registra en la ventana."""
    if not _HABILITADO:
        return True
    ahora = time.time()
    with _bloqueo:
        ventana = [t for t in _baldes[clave] if ahora - t < VENTANA_SEGUNDOS]
        if len(ventana) >= max_peticiones:
            _baldes[clave] = ventana
            return False
        ventana.append(ahora)
        _baldes[clave] = ventana
        _podar(ahora)
        return True


def limitar(max_peticiones: int):
    """Crea una dependencia de FastAPI que limita peticiones por IP."""

    def _dep(request: Request):
        if not registrado(f"ip:{_ip(request)}", max_peticiones):
            raise HTTPException(
                status_code=429,
                detail="Demasiadas peticiones. Intenta de nuevo en unos segundos.",
            )

    return _dep


def limpiar() -> None:
    """Vacía el estado del limitador (uso en pruebas)."""
    with _bloqueo:
        _baldes.clear()


# Dependencias concretas reutilizables.
limitar_scan = limitar(LIMITE_SCAN)
limitar_login = limitar(LIMITE_LOGIN)
limitar_pdf = limitar(LIMITE_PDF)
limitar_zip = limitar(LIMITE_ZIP)
