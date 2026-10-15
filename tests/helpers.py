"""Utilidades compartidas por los tests."""

from app.models.coreModule.product import Product

API = "/api/v1"


def item(product: Product, cant: int, unit_price: str | None = None) -> dict:
    """Renglón de pedido; por defecto usa el precio base del producto."""
    return {
        "id_product": product.id_product,
        "cant": cant,
        "unit_price": unit_price or str(product.base_price),
    }
