"""Archivado mensual (H3): configuración del spreadsheet por año y bitácora."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.api.dependencies import CurrentUser, get_current_user
from app.main import app
from app.models.coreModule.monthly_archive import MonthlyArchive
from app.utils.enums.archive_status import ArchiveStatus
from tests.helpers import API

URL = f"{API}/archive"
SHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abc"


@pytest.fixture()
def admin(client, data):
    """El mismo TestClient, autenticado como ADMINISTRADOR."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user=data.taker, roles=["ADMINISTRADOR"]
    )
    return client


def test_solo_admin(client):
    assert client.get(f"{URL}/").status_code == 403
    assert client.get(f"{URL}/spreadsheets").status_code == 403
    assert (
        client.put(f"{URL}/spreadsheets/2026", json={"spreadsheet": SHEET_ID}).status_code
        == 403
    )


def test_registrar_spreadsheet_por_id(admin):
    response = admin.put(f"{URL}/spreadsheets/2026", json={"spreadsheet": SHEET_ID})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["year"] == 2026
    assert body["spreadsheet_id"] == SHEET_ID
    assert body["url"] == f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"


def test_registrar_spreadsheet_pegando_la_url(admin):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"

    response = admin.put(f"{URL}/spreadsheets/2026", json={"spreadsheet": url})

    assert response.status_code == 200, response.text
    assert response.json()["spreadsheet_id"] == SHEET_ID


def test_actualizar_y_listar_spreadsheets(admin):
    other = "9ZyXwVuTsRqPoNmLkJiHgFeDcBa9876543210"
    admin.put(f"{URL}/spreadsheets/2026", json={"spreadsheet": SHEET_ID})
    admin.put(f"{URL}/spreadsheets/2027", json={"spreadsheet": SHEET_ID})
    admin.put(f"{URL}/spreadsheets/2026", json={"spreadsheet": other})

    rows = admin.get(f"{URL}/spreadsheets").json()

    assert [(r["year"], r["spreadsheet_id"]) for r in rows] == [
        (2027, SHEET_ID),
        (2026, other),
    ]


@pytest.mark.parametrize(
    ("year", "value"),
    [
        (2026, "no es un id"),
        (2026, "corto"),
        (2026, "https://docs.google.com/document/d/abc/edit"),
        (2019, SHEET_ID),
        (2101, SHEET_ID),
    ],
)
def test_valores_invalidos(admin, year, value):
    response = admin.put(f"{URL}/spreadsheets/{year}", json={"spreadsheet": value})

    assert response.status_code == 422


def test_bitacora_del_mas_reciente_al_mas_antiguo(admin, db):
    entries = (
        (date(2026, 8, 1), ArchiveStatus.PURGED),
        (date(2026, 9, 1), ArchiveStatus.EXPORTED),
    )
    for month, status in entries:
        db.add(
            MonthlyArchive(
                archive_month=month,
                status=status,
                spreadsheet_id=SHEET_ID,
                sheet_title=f"{month:%Y-%m}",
                orders_count=10,
                rows_count=25,
                total_sales=Decimal("150000.00"),
                exported_at=datetime(2026, 10, 1, 12, tzinfo=UTC),
            )
        )
    db.commit()

    rows = admin.get(f"{URL}/").json()

    assert [(r["month"], r["status"]) for r in rows] == [
        ("2026-09", "EXPORTED"),
        ("2026-08", "PURGED"),
    ]
    assert rows[0]["sheet_title"] == "2026-09"
