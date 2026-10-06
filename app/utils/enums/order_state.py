import enum


class OrderState(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
