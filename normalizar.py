def normalizar_nombre(texto: str, conservar_siglas: bool = False) -> str:
    """Limpia espacios sobrantes sin alterar mayúsculas ni minúsculas.

    El usuario escribe el nombre, apellido o cargo tal como desea verlo;
    solo se recortan espacios al inicio/fin y se colapsan espacios dobles.
    El parámetro conservar_siglas se mantiene por compatibilidad pero no
    tiene efecto.
    """
    if not texto:
        return ""
    return " ".join(texto.split())


def normalizar_correo(texto: str) -> str:
    return (texto or "").strip().lower()
