"""Consultas del panel de domiciliarios.

Un domiciliario es un usuario con el rol VENDEDOR: la fila base es su `user_role` de
VENDEDOR (único por usuario), unida a `app_user` y `person`. Sus asignaciones son las
filas de `user_vehicle` de ese `user_role`.
"""

from typing import Any

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.config import settings
from app.models.coreModule.order import Order
from app.models.coreModule.shift_closure import ShiftClosure
from app.models.coreModule.user_vehicle import UserVehicle
from app.models.parametersModule.vehicle import Vehicle
from app.models.securityModule.person import Person
from app.models.securityModule.role import Role
from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
from app.repositories.pagination import paginate
from app.schemas.common.page_schema import PageParams
from app.schemas.coreModule.driver_schema import DriverAdminFilters

# Nombre del rol en user_role_type (seeds y claim del JWT)
SELLER_ROLE = "VENDEDOR"


def _seller_role_id():
    return select(Role.id_role).where(Role.name == SELLER_ROLE).scalar_subquery()


class RepositoryDriver:
    # ------------------------------------------------------------------
    # Domiciliarios
    # ------------------------------------------------------------------
    @staticmethod
    def _conditions(filters: DriverAdminFilters) -> list[Any]:
        conditions: list[Any] = [UserRole.id_role == _seller_role_id()]
        if filters.search:
            full_name = Person.name + " " + Person.last_name
            has_code = (
                exists()
                .where(
                    UserVehicle.id_user_role == UserRole.id_user_role,
                    UserVehicle.code.startswith(filters.search, autoescape=True),
                )
                .correlate(UserRole)
            )
            conditions.append(
                or_(full_name.icontains(filters.search, autoescape=True), has_code)
            )
        if filters.active is not None:
            conditions.append(User.active.is_(filters.active))
        return conditions

    @staticmethod
    def _select() -> Select:
        """Fila del listado. Códigos y conteo de asignaciones activas, y si está
        protegido: subconsultas que solo se calculan para las filas de la página."""
        active_assignment = (
            UserVehicle.id_user_role == UserRole.id_user_role,
            UserVehicle.active.is_(True),
        )
        codes = (
            # El orden lo pone el schema (DriverAdminRow.codes)
            select(func.array_agg(UserVehicle.code))
            .where(*active_assignment)
            .correlate(UserRole)
            .scalar_subquery()
        )
        assignments_count = (
            select(func.count(UserVehicle.id_user_vehicle))
            .where(*active_assignment)
            .correlate(UserRole)
            .scalar_subquery()
        )
        # Protegido: tiene otro rol (p. ej. ADMINISTRADOR) o es el vendedor por defecto
        other_role = aliased(UserRole)
        has_other_role = (
            exists()
            .where(
                other_role.id_user == UserRole.id_user,
                other_role.id_role != UserRole.id_role,
            )
            .correlate(UserRole)
        )
        is_default_seller = (
            exists()
            .where(
                UserVehicle.id_user_role == UserRole.id_user_role,
                UserVehicle.code == settings.DEFAULT_SELLER_CODE,
            )
            .correlate(UserRole)
        )
        return (
            select(
                User.id_user,
                Person.id_person,
                Person.name,
                Person.last_name,
                Person.phone,
                Person.email,
                User.username,
                User.active,
                codes.label("codes"),
                assignments_count.label("assignments_count"),
                or_(has_other_role, is_default_seller).label("protected"),
            )
            .select_from(UserRole)
            .join(User, User.id_user == UserRole.id_user)
            .join(Person, Person.id_person == User.id_person)
        )

    # Una página de domiciliarios, por nombre
    def get_admin_page(
        self, db: Session, filters: DriverAdminFilters, params: PageParams
    ) -> tuple[list[Any], int]:
        conditions = self._conditions(filters)
        stmt = (
            self._select()
            .where(*conditions)
            .order_by(Person.name, Person.last_name, User.id_user)
        )
        count_stmt = (
            select(UserRole.id_user_role)
            .join(User, User.id_user == UserRole.id_user)
            .join(Person, Person.id_person == User.id_person)
            .where(*conditions)
        )
        return paginate(db, stmt, params, count_stmt=count_stmt)

    def get_admin_row(self, db: Session, id_user: int) -> Any | None:
        stmt = self._select().where(
            UserRole.id_role == _seller_role_id(), User.id_user == id_user
        )
        return db.execute(stmt).one_or_none()

    # user_role de VENDEDOR del usuario (None = no es domiciliario)
    def get_seller_role(self, db: Session, id_user: int) -> UserRole | None:
        stmt = select(UserRole).where(
            UserRole.id_user == id_user, UserRole.id_role == _seller_role_id()
        )
        return db.scalar(stmt)

    def get_role_id(self, db: Session) -> int | None:
        return db.scalar(select(Role.id_role).where(Role.name == SELLER_ROLE))

    # ¿Tiene algún rol además de VENDEDOR? (no se desactiva desde este panel)
    def has_other_roles(self, db: Session, id_user: int) -> bool:
        stmt = select(
            exists().where(
                UserRole.id_user == id_user, UserRole.id_role != _seller_role_id()
            )
        )
        return bool(db.scalar(stmt))

    # Usuarios que ya empiezan por `base` (para generar uno libre: base, base2…)
    def usernames_like(self, db: Session, base: str) -> set[str]:
        stmt = select(User.username).where(
            User.username.startswith(base, autoescape=True)
        )
        return set(db.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Asignaciones (user_vehicle)
    # ------------------------------------------------------------------
    @staticmethod
    def _in_use():
        """La asignación tiene pedidos o cierres (los índices de sale_order y
        shift_closure por id_user_vehicle hacen baratos estos EXISTS)."""
        return or_(
            exists()
            .where(Order.id_user_vehicle == UserVehicle.id_user_vehicle)
            .correlate(UserVehicle),
            exists()
            .where(ShiftClosure.id_user_vehicle == UserVehicle.id_user_vehicle)
            .correlate(UserVehicle),
        )

    def _assignments_select(self) -> Select:
        return select(
            UserVehicle.id_user_vehicle,
            UserVehicle.code,
            UserVehicle.active,
            Vehicle.id_vehicle,
            Vehicle.name.label("vehicle_name"),
            Vehicle.active.label("vehicle_active"),
            self._in_use().label("in_use"),
            (UserVehicle.code == settings.DEFAULT_SELLER_CODE).label("is_default"),
        ).join(Vehicle, Vehicle.id_vehicle == UserVehicle.id_vehicle)

    def get_assignments(self, db: Session, id_user_role: int) -> list[Any]:
        stmt = (
            self._assignments_select()
            .where(UserVehicle.id_user_role == id_user_role)
            .order_by(UserVehicle.code)
        )
        return list(db.execute(stmt).all())

    def get_assignment_row(self, db: Session, id_user_vehicle: int) -> Any | None:
        stmt = self._assignments_select().where(
            UserVehicle.id_user_vehicle == id_user_vehicle
        )
        return db.execute(stmt).one_or_none()

    def is_in_use(self, db: Session, id_user_vehicle: int) -> bool:
        stmt = select(
            or_(
                exists().where(Order.id_user_vehicle == id_user_vehicle),
                exists().where(ShiftClosure.id_user_vehicle == id_user_vehicle),
            )
        )
        return bool(db.scalar(stmt))

    # ¿Este user_role tiene la asignación del vendedor por defecto del cierre?
    def owns_default_seller(self, db: Session, id_user_role: int) -> bool:
        stmt = select(
            exists().where(
                UserVehicle.id_user_role == id_user_role,
                UserVehicle.code == settings.DEFAULT_SELLER_CODE,
            )
        )
        return bool(db.scalar(stmt))

    def used_codes(self, db: Session) -> set[str]:
        return {code.strip() for code in db.scalars(select(UserVehicle.code)).all()}


driver_repository = RepositoryDriver()
