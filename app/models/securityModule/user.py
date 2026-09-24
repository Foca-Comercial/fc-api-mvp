from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.securityModule.person import Person
    from app.models.securityModule.user_role import UserRole


class User(Base):
    __tablename__ = "app_user"
    __table_args__ = (Index("idx_app_user_person", "id_person"),)

    id_user: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Clave Foranea
    id_person: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("person.id_person", ondelete="RESTRICT"), nullable=False
    )
    person: Mapped["Person"] = relationship(back_populates="users")

    # PNI
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user")
