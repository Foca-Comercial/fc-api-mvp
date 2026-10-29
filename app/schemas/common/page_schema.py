"""Listados paginados en el servidor (vistas de administración).

Contrato común de todos los listados paginados:

    GET /xxx/admin?page=1&page_size=25&search=...
    -> {"page": 1, "page_size": 25, "total": 134, "pages": 6, "items": [...]}

`PageParams` llega al servicio ya validado (ver `get_page_params` en
app/api/dependencies.py); el repositorio pagina con `paginate` de
app/repositories/pagination.py y el servicio arma la respuesta con `Page.build`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

# Tamaño de página por defecto y máximo permitido (igual que el histórico)
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200

ItemType = TypeVar("ItemType")


@dataclass(frozen=True)
class PageParams:
    """Página pedida (1 = la primera) y su tamaño."""

    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[ItemType]):
    page: int
    page_size: int
    total: int = Field(..., description="Registros que cumplen el filtro")
    pages: int = Field(..., description="Total de páginas (0 si no hay registros)")
    items: list[ItemType]

    @classmethod
    def build(
        cls, items: Sequence[ItemType], *, total: int, params: PageParams
    ) -> "Page[ItemType]":
        """Arma la página. Los `items` deben ser ya instancias del schema de la
        fila (p. ej. `Row.model_validate(row, from_attributes=True)`)."""
        return cls(
            page=params.page,
            page_size=params.page_size,
            total=total,
            pages=-(-total // params.page_size),  # división hacia arriba
            items=list(items),
        )
