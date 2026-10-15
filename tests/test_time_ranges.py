"""Rangos de día y mes en hora de Bogotá (UTC-5, sin horario de verano)."""

from datetime import UTC, date, datetime

from sqlalchemy import func, select

from app.core.timezone import bogota_date_range, bogota_day_range, bogota_month_range
from app.models.coreModule.order import Order
from app.repositories.time_filters import on_bogota_day, on_db_today


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_rango_de_un_dia():
    start, end = bogota_day_range(date(2026, 10, 14))

    assert start == _utc(2026, 10, 14, 5, 0)
    assert end == _utc(2026, 10, 15, 5, 0)


def test_rango_de_mes_incluido_el_cambio_de_anio():
    assert bogota_month_range(2026, 10) == (
        _utc(2026, 10, 1, 5, 0),
        _utc(2026, 11, 1, 5, 0),
    )
    assert bogota_month_range(2026, 12) == (
        _utc(2026, 12, 1, 5, 0),
        _utc(2027, 1, 1, 5, 0),
    )


def test_rango_entre_fechas_incluye_ambos_dias():
    start, end = bogota_date_range(date(2026, 10, 1), date(2026, 10, 31))

    assert start == _utc(2026, 10, 1, 5, 0)
    assert end == _utc(2026, 11, 1, 5, 0)


def _count(db, condition) -> int:
    return db.scalar(select(func.count()).select_from(Order).where(condition))


def test_filtro_por_dia_respeta_la_medianoche_de_bogota(db, create_order):
    """23:30 del 14 en Bogotá (04:30 UTC del 15) pertenece al día 14."""
    late = create_order()
    early = create_order()
    db.get(Order, late["id_order"]).creation_datetime = _utc(2026, 10, 15, 4, 30)
    db.get(Order, early["id_order"]).creation_datetime = _utc(2026, 10, 15, 5, 0)
    db.flush()

    ids_14 = set(
        db.scalars(
            select(Order.id_order).where(
                on_bogota_day(Order.creation_datetime, date(2026, 10, 14))
            )
        )
    )

    assert late["id_order"] in ids_14
    assert early["id_order"] not in ids_14  # 00:00 del 15 en Bogotá


def test_filtro_hoy_segun_la_bd(db, create_order):
    order = create_order()  # creation_datetime = now() de la transacción

    assert _count(db, on_db_today(Order.creation_datetime)) >= 1
    db.get(Order, order["id_order"]).creation_datetime = _utc(2020, 1, 1, 12, 0)
    db.flush()
    assert _count(
        db,
        on_db_today(Order.creation_datetime) & (Order.id_order == order["id_order"]),
    ) == 0
