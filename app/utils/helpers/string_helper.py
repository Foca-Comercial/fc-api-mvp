import re

_WHITESPACE = re.compile(r"\s+")


def comparison_key(value: str) -> str:
    """Clave para comparar unicidad: mayúsculas y sin ningún espacio."""
    return _WHITESPACE.sub("", value).upper()
