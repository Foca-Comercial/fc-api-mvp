"""Paginación en SQL para los listados de administración.

Recibe la consulta completa (filtros y orden incluidos) y devuelve solo la página
pedida más el total de registros del filtro. La paginación ocurre en PostgreSQL
(OFFSET/LIMIT), nunca trayendo todas las filas a Python.

    rows, total = paginate(db, stmt, params)                 # filas (Row)
    clients, total = paginate(db, stmt, params, scalars=True)  # entidades ORM

El orden de `stmt` debe terminar en una columna única (normalmente la PK) para
que las páginas sean estables: con empates, PostgreSQL puede repetir u omitir
filas entre una página y otra. `order_clause` lo arma a partir del orden pedido
(`sort_by` / `sort_dir`) y de los campos que el listado permite ordenar:

    stmt = stmt.order_by(*order_clause(
        params,
        {"name": Client.name, "routes_count": "routes_count"},  # "x" = alias del select
        default=[Client.name],
        tiebreak=Client.id_client,
    ))
"""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Select, asc, desc, func, literal_column, select
from sqlalchemy.orm import Session

from app.schemas.common.page_schema import PageParams
from app.utils.exceptions.business_exceptions import BusinessValidationError

# Valor de un campo ordenable: una columna o expresión, el alias (str) de una
# columna del SELECT, o una tupla de ellos para ordenar por varias a la vez.
SortField = Any


def order_clause(
    params: PageParams,
    fields: Mapping[str, SortField],
    *,
    default: Sequence[SortField],
    tiebreak: Any,
) -> list[Any]:
    """ORDER BY del listado: el campo pedido (o el orden por defecto) en la
    dirección pedida, nulos al final y la PK como desempate.

    Solo se ordena por los campos de `fields` (lista blanca): el texto recibido
    nunca se convierte en SQL. Uno que no esté -> 422 INVALID_SORT_FIELD.
    """
    if params.sort_by is None:
        columns = list(default)
    elif params.sort_by in fields:
        value = fields[params.sort_by]
        columns = list(value) if isinstance(value, tuple) else [value]
    else:
        valid = ", ".join(sorted(fields))
        raise BusinessValidationError(
            f"No se puede ordenar por '{params.sort_by}'. Campos válidos: {valid}.",
            field="sort_by",
            code="INVALID_SORT_FIELD",
        )
    direction = desc if params.sort_dir == "desc" else asc
    resolved = [literal_column(c) if isinstance(c, str) else c for c in columns]
    return [direction(c).nulls_last() for c in resolved] + [direction(tiebreak)]


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
