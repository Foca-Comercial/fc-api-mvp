"""Paginación en SQL para los listados de administración.

Recibe la consulta completa (filtros y orden incluidos) y devuelve solo la página
pedida más el total de registros del filtro. La paginación ocurre en PostgreSQL
(OFFSET/LIMIT), nunca trayendo todas las filas a Python.

    rows, total = paginate(db, stmt, params)                 # filas (Row)
    clients, total = paginate(db, stmt, params, scalars=True)  # entidades ORM

El orden de `stmt` debe terminar en una columna única (normalmente la PK) para
que las páginas sean estables: con empates, PostgreSQL puede repetir u omitir
filas entre una página y otra.
"""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.schemas.common.page_schema import PageParams


def count_rows(db: Session, stmt: Select) -> int:
    """Cantidad de filas que devuelve `stmt` (sin su ORDER BY, que no cambia el
    conteo y solo le cuesta trabajo a la BD)."""
    subquery = stmt.order_by(None).subquery()
    return db.scalar(select(func.count()).select_from(subquery)) or 0


def paginate(
    db: Session,
    stmt: Select,
    params: PageParams,
    *,
    scalars: bool = False,
    count_stmt: Select | None = None,
) -> tuple[list[Any], int]:
    """(filas de la página, total del filtro).

    `count_stmt` permite contar con una consulta más liviana (p. ej. sin los
    joins que solo aportan columnas para mostrar); debe aplicar los mismos
    filtros que `stmt`.
    """
    total = count_rows(db, count_stmt if count_stmt is not None else stmt)
    # Sin registros, o una página más allá del final: no hace falta la 2.ª consulta
    if total == 0 or params.offset >= total:
        return [], total

    page_stmt = stmt.offset(params.offset).limit(params.page_size)
    result = db.scalars(page_stmt) if scalars else db.execute(page_stmt)
    return list(result.all()), total
