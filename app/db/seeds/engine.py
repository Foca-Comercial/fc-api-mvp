import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.seeds.loader import load_records

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeedSpec:
    file: str
    model: type[Base]
    schema: type[BaseModel]
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _validate(spec: SeedSpec, index: int, raw: dict[str, Any]) -> dict[str, Any]:
    unknown = set(raw) - set(spec.schema.model_fields)
    if unknown:
        raise ValueError(f"{spec.file} #{index + 1}: campos desconocidos {unknown}")

    record = spec.transform(dict(raw)) if spec.transform else dict(raw)
    try:
        return spec.schema.model_validate(record).model_dump()
    except ValueError as error:
        raise ValueError(f"{spec.file} #{index + 1}: {error}") from error


def seed_entity(db: Session, spec: SeedSpec) -> int:
    table = spec.model.__tablename__

    if db.scalar(select(func.count()).select_from(spec.model)):
        logger.info("%-22s omitida (la tabla ya tiene datos)", table)
        return 0

    records = load_records(spec.file)
    objects = [
        spec.model(**_validate(spec, index, raw)) for index, raw in enumerate(records)
    ]
    db.add_all(objects)
    db.flush()

    # Las relaciones del JSON asumen que el registro N recibe el ID N.
    pk_name = sa_inspect(spec.model).primary_key[0].key
    generated = [getattr(obj, pk_name) for obj in objects]  # type: ignore
    expected = list(range(1, len(objects) + 1))
    if generated != expected:
        raise RuntimeError(
            f"{table}: los IDs generados {generated[:5]}... no coinciden con los "
            f"esperados {expected[:5]}... Reinicia la secuencia de la tabla "
            "(p. ej. TRUNCATE ... RESTART IDENTITY en PostgreSQL) y reintenta."
        )

    logger.info("%-22s %d registros insertados", table, len(objects))
    return len(objects)
