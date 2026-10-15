from datetime import date

from sqlalchemy import CheckConstraint, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class DailyOrderCounter(Base):
    """Último consecutivo de pedido (purchase_order) usado en cada día de Bogotá.

    Una fila por día. Se incrementa con un INSERT ... ON CONFLICT DO UPDATE dentro
    de la transacción que crea el pedido: la fila queda bloqueada hasta el commit,
    así dos pedidos simultáneos nunca reciben el mismo número, y si la creación
    falla el incremento se revierte (no quedan huecos).
    """

    __tablename__ = "daily_order_counter"
    __table_args__ = (
        CheckConstraint("last_value > 0", name="chk_daily_order_counter_value"),
    )

    counter_date: Mapped[date] = mapped_column(Date, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False)
