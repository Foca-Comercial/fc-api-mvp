"""Comprobante de despacho (cambio final B5): solo POS + efectivo y datos de entrega."""

import pytest
from reportlab.pdfgen import canvas

from app.models.coreModule.client import Client
from app.services.coreModule.order_service import order_service
from app.services.pdf.pdf_service import pdf_service
from tests.helpers import API


def _receipt(client, order: dict):
    client.post(f"{API}/orders/{order['id_order']}/dispatch")
    return client.get(f"{API}/orders/{order['id_order']}/receipt")


def _drawn_text(db, id_order: int, monkeypatch) -> list[str]:
    """Textos que el CD dibuja (el PDF va comprimido, así que se capturan al dibujar)."""
    drawn: list[str] = []
    original = canvas.Canvas.drawString

    def spy(self, x, y, text, *args, **kwargs):
        drawn.append(text)
        return original(self, x, y, text, *args, **kwargs)

    monkeypatch.setattr(canvas.Canvas, "drawString", spy)
    pdf_service.generate_dispatch_receipt(order_service.get_full_detail(db, id_order))
    return drawn


def test_pos_en_efectivo_genera_el_cd(client, create_order):
    response = _receipt(client, create_order())

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")


@pytest.mark.parametrize(
    "billing",
    [
        {"payment_method": "TRANSFER"},
        {"payment_method": "CREDIT"},
        {"invoice_type": "ELECTRONIC"},
    ],
)
def test_sin_cd_fuera_de_pos_en_efectivo(client, create_order, billing):
    response = _receipt(client, create_order(**billing))

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "RECEIPT_NOT_AVAILABLE"


def test_sin_cd_aunque_no_este_despachado(client, create_order):
    order = create_order(payment_method="TRANSFER")

    response = client.get(f"{API}/orders/{order['id_order']}/receipt")

    assert response.json()["code"] == "RECEIPT_NOT_AVAILABLE"


def test_datos_de_entrega_sin_direccion_ni_telefono(client, create_order, db, monkeypatch):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    drawn = _drawn_text(db, order["id_order"], monkeypatch)

    assert "DATOS DE ENTREGA" in drawn
    assert "CLIENTE REGISTRADO" in drawn
    assert "BARRIO TEST" in drawn
    assert "ZONA TEST" in drawn
    # Dirección y teléfono, en cada una de las dos pasadas (medir y dibujar)
    assert drawn.count("NO REGISTRA") == 4
    # Ya no sale el cliente genérico
    assert "CUANTÍAS MENORES" not in drawn


def test_datos_de_entrega_con_direccion_larga(client, create_order, db, data, monkeypatch):
    client_row = db.get(Client, data.client.id_client)
    client_row.address = "Carrera 15 # 23-45 Conjunto Los Almendros torre 3 apto 502"
    client_row.phone = "3001234567"
    db.flush()
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    drawn = _drawn_text(db, order["id_order"], monkeypatch)

    assert "3001234567" in drawn
    assert "NO REGISTRA" not in drawn
    # La dirección larga parte en varias líneas sin perder texto
    address = "CARRERA 15 # 23-45 CONJUNTO LOS ALMENDROS TORRE 3 APTO 502"
    start = drawn.index("Dirección") + 1
    end = drawn.index("Barrio")
    assert end - start >= 2
    assert " ".join(drawn[start:end]) == address
