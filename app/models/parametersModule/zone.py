from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.parametersModule.neighborhood import Neighborhood


class Zone(Base):
    __tablename__ = "zone"

    id_zone: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    commune_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # PNI
    neighborhoods: Mapped[list["Neighborhood"]] = relationship(back_populates="zone")
