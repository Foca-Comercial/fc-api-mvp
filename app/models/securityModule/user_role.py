from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.user_vehicle import UserVehicle
    from app.models.securityModule.role import Role
    from app.models.securityModule.user import User


class UserRole(Base):
    __tablename__ = "user_role"
    __table_args__ = (
        UniqueConstraint("id_user", "id_role", name="uq_user_role"),
        Index("idx_user_role_user", "id_user"),
        Index("idx_user_role_role", "id_role"),
    )

    id_user_role: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    # Claves Foraneras
    id_user: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("app_user.id_user", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="user_roles")

    id_role: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user_role_type.id_role", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped["Role"] = relationship(back_populates="user_roles")

    # PNI
    user_vehicles: Mapped[list["UserVehicle"]] = relationship(
        back_populates="user_role"
    )
