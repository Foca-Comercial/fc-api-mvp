from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.client import Client
    from app.models.parametersModule.zone import Zone


class Neighborhood(Base):
    __tablename__ = "neighborhood"
    __table_args__ = (Index("idx_neighborhood_zone", "id_zone"),)

    id_neighborhood: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Clave Foranera
    id_zone: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("zone.id_zone", ondelete="RESTRICT"), nullable=False
    )
    zone: Mapped["Zone"] = relationship(back_populates="neighborhoods")

    # PNI
    clients: Mapped[list["Client"]] = relationship(back_populates="neighborhood")
