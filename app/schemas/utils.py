import copy
from typing import Any, Optional, Type, TypeVar  # noqa: F401, UP035

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

ModelT = TypeVar("ModelT", bound=BaseModel)


def partial_model(model: type[ModelT]) -> type[ModelT]:
    """
    Decorador de clase: toma un modelo Pydantic y genera una nueva versión
    donde TODOS los campos son opcionales (default=None), sin perder las
    validaciones originales (max_length, description, etc.).

    Nota: Pydantic soporta esta generación dinámica en tiempo de ejecución
    sin problema, pero sus stubs de tipado no logran describirla con
    precisión. Los `# type: ignore` en este archivo no ocultan errores
    reales — son el límite del análisis estático frente a código
    intencionalmente dinámico.

    Uso:
        @partial_model
        class PersonUpdate(PersonBase):
            pass
    """

    def make_optional(field_info: FieldInfo) -> tuple[Any, FieldInfo]:
        new_field = copy.deepcopy(field_info)
        new_field.default = None
        new_field.annotation = Optional[field_info.annotation]  # type: ignore  # noqa: UP045
        return new_field.annotation, new_field

    fields: dict[str, Any] = {
        name: make_optional(field_info)
        for name, field_info in model.model_fields.items()
    }

    return create_model(  # type: ignore
        model.__name__,
        __base__=model,
        __module__=model.__module__,
        **fields,
    )
