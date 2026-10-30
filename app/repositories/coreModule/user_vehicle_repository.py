from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coreModule.user_vehicle import UserVehicle
from app.models.parametersModule.vehicle import Vehicle
from app.models.securityModule.person import Person
from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.user_vehicle_schema import (
    UserVehicleCreate,
    UserVehicleUpdate,
)


class RepositoryUserVehicle(
    BaseRepository[UserVehicle, UserVehicleCreate, UserVehicleUpdate]
):
    # Listado de las asignaciones Conductor-Vehiculo ordenado por nombre conductor
    def get_all_ordered_by_driver_name(
        self, db: Session, *, only_active: bool = True
    ) -> list[tuple[int, str, str, str]]:
        stmt = (
            select(
                UserVehicle.id_user_vehicle,
                UserVehicle.code,
                (Person.name + " " + Person.last_name).label("driver_name"),
                Vehicle.name.label("vehicle_name"),
            )
            .join(UserRole, UserVehicle.id_user_role == UserRole.id_user_role)
            .join(User, UserRole.id_user == User.id_user)
            .join(Person, User.id_person == Person.id_person)
            .join(Vehicle, UserVehicle.id_vehicle == Vehicle.id_vehicle)
        )

        if only_active:
            stmt = stmt.where(
                UserVehicle.active.is_(True),
                User.active.is_(True),
                Person.active.is_(True),
                Vehicle.active.is_(True),
            )

        stmt = stmt.order_by(Person.name.asc(), Person.last_name.asc())
        return list(db.execute(stmt).all())

    # Vista Cierre: código y nombre de los vendedores indicados
    # {id_user_vehicle: (code, seller_name)}. No filtra inactivos: un pedido ya
    # despachado se factura aunque el vendedor se haya desactivado después.
    def get_sellers(
        self, db: Session, ids: Collection[int]
    ) -> dict[int, tuple[str, str]]:
        if not ids:
            return {}
        stmt = (
            select(
                UserVehicle.id_user_vehicle,
                UserVehicle.code,
                (Person.name + " " + Person.last_name).label("seller_name"),
            )
            .join(UserRole, UserVehicle.id_user_role == UserRole.id_user_role)
            .join(User, UserRole.id_user == User.id_user)
            .join(Person, User.id_person == Person.id_person)
            .where(UserVehicle.id_user_vehicle.in_(ids))
        )
        return {
            row.id_user_vehicle: (row.code, row.seller_name)
            for row in db.execute(stmt).all()
        }

    # Para asignar pedidos: estado de la asignación, su vehículo y su domiciliario
    # (usuario y persona). None si la asignación no existe.
    def get_assignment_status(self, db: Session, id_user_vehicle: int):
        stmt = (
            select(
                UserVehicle.active,
                Vehicle.active.label("vehicle_active"),
                Vehicle.name.label("vehicle_name"),
                (User.active & Person.active).label("driver_active"),
                (Person.name + " " + Person.last_name).label("driver_name"),
            )
            .join(Vehicle, UserVehicle.id_vehicle == Vehicle.id_vehicle)
            .join(UserRole, UserVehicle.id_user_role == UserRole.id_user_role)
            .join(User, UserRole.id_user == User.id_user)
            .join(Person, User.id_person == Person.id_person)
            .where(UserVehicle.id_user_vehicle == id_user_vehicle)
        )
        return db.execute(stmt).one_or_none()

    def get_id_by_code(self, db: Session, code: str) -> int | None:
        return db.scalar(
            select(UserVehicle.id_user_vehicle).where(UserVehicle.code == code)
        )


# Intancia del repositorio inyectando el modelo ORM
user_vehicle_repository = RepositoryUserVehicle(UserVehicle)
