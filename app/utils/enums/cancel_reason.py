import enum


class CancelReason(str, enum.Enum):
    """Motivo obligatorio al cancelar un pedido."""

    WRONG_BILLING = "WRONG_BILLING"  # mal facturado
    CLIENT_ABSENT = "CLIENT_ABSENT"  # el cliente no estaba
    DAMAGED_PRODUCT = "DAMAGED_PRODUCT"  # producto dañado
    OTHER = "OTHER"
