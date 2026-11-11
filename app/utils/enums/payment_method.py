import enum


class PaymentMethod(str, enum.Enum):
    """Cómo paga el cliente el pedido. Solo el efectivo en factura POS lleva CD y
    entra al consolidado del cierre; el resto se factura aparte en Siigo."""

    CASH = "CASH"
    TRANSFER = "TRANSFER"
    CREDIT = "CREDIT"  # informativo: el sistema no lleva cartera
