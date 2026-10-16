import enum


class ArchiveStatus(str, enum.Enum):
    EXPORTED = "EXPORTED"  # exportado a Sheets; los pedidos siguen en la BD
    PURGED = "PURGED"  # exportado y eliminado de la BD
