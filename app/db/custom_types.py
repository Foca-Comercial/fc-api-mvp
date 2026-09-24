from enum import IntEnum
from typing import TypeVar

from sqlalchemy import Integer
from sqlalchemy.types import TypeDecorator

E = TypeVar("E", bound=IntEnum)


class IntEnumType(TypeDecorator):
    """
    Permite mapear un IntEnum de Python a una columna Integer en la BD.
    Guarda el valor numérico (enum.value) y, al leer, lo reconstruye
    automáticamente como instancia del IntEnum correspondiente.
    """

    impl = Integer
    cache_ok = True

    def __init__(self, enum_class: type[E], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        # Python -> BD (al hacer INSERT/UPDATE)
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return int(value)
        return value

    def process_result_value(self, value, dialect):
        # BD -> Python (al leer una fila)
        if value is None:
            return None
        return self.enum_class(value)
