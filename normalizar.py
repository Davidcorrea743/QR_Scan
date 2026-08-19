PALABRAS_MINUSCULA = {
    "de",
    "del",
    "la",
    "las",
    "los",
    "el",
    "y",
    "e",
    "a",
    "al",
    "da",
    "do",
    "das",
    "dos",
    "van",
    "von",
}


def normalizar_nombre(texto: str, conservar_siglas: bool = False) -> str:
    """Normaliza un nombre, apellido o cargo a mayúscula inicial por palabra.

    Ej.: "pEpITO PEREZ" -> "Pepito Perez". Con conservar_siglas=True, en texto
    mixto mantiene siglas cortas en mayúsculas (ej. "Desarrollador RRHH"),
    pero si todo el texto viene en mayúsculas se normaliza por completo.
    """
    if not texto:
        return ""
    palabras = texto.strip().split()
    if not palabras:
        return ""
    todo_mayusculas = len(palabras) > 1 and all(
        p.isupper() for p in palabras if p.isalpha()
    )
    resultado = []
    for palabra in palabras:
        if palabra.lower() in PALABRAS_MINUSCULA:
            resultado.append(palabra.lower())
        elif conservar_siglas and not todo_mayusculas and palabra.isupper() and (
            len(palabra) <= 4 or any(c.isdigit() for c in palabra)
        ):
            resultado.append(palabra)
        else:
            resultado.append(palabra.capitalize())
    return " ".join(resultado)


def normalizar_correo(texto: str) -> str:
    return (texto or "").strip().lower()