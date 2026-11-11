import enum


class InvoiceType(str, enum.Enum):
    """Tipo de factura del pedido. Se copia del cliente al crear el pedido
    (client.requires_electronic_invoice) y se puede cambiar por pedido."""

    POS = "POS"
    ELECTRONIC = "ELECTRONIC"
