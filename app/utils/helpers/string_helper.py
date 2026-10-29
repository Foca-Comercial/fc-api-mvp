import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def comparison_key(value: str) -> str:
    """Clave para comparar unicidad: mayúsculas y sin ningún espacio."""
    return _WHITESPACE.sub("", value).upper()


_NON_ALNUM = re.compile(r"[^a-z0-9]")


def ascii_slug(value: str) -> str:
    """Minúsculas ASCII sin tildes ni símbolos: "José Peña" -> "josepena"."""
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return _NON_ALNUM.sub("", plain.lower())


def username_base(name: str, last_name: str) -> str:
    """Usuario sugerido "nombre.apellido" con la primera palabra de cada uno, igual
    que los usuarios de la data inicial: ("JOSÉ LUIS", "PEÑA ROJAS") -> "jose.pena"."""
    first = ascii_slug(name.split()[0]) if name.split() else ""
    last = ascii_slug(last_name.split()[0]) if last_name.split() else ""
    return ".".join(part for part in (first, last) if part) or "domiciliario"
