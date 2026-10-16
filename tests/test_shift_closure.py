"""Vista de Cierre (C1): CRUD de shift_closure de solo lectura."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.coreModule.shift_closure import ShiftClosure
from tests.helpers import API

URL = f"{API}/shifts_closures"


def test_el_crud_es_de_solo_lectura(admin):
    assert admin.get(f"{URL}/").status_code == 200
    assert admin.post(f"{URL}/", json={}).status_code == 405
    assert admin.patch(f"{URL}/1", json={}).status_code == 405
    assert admin.delete(f"{URL}/1").status_code == 405


def test_un_cierre_por_vendedor_y_dia(db, data):
    def closure():
        return ShiftClosure(
            closure_date=date(2026, 10, 15),
            id_user_vehicle=data.user_vehicle.id_user_vehicle,
            total_orders=1,
            total_sales=Decimal("1000"),
        )

    db.add(closure())
    db.flush()
    db.add(closure())

    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
