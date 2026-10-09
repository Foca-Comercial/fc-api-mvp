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
                User.active.is_(True),
                Person.active.is_(True),
                Vehicle.active.is_(True),
            )

        stmt = stmt.order_by(Person.name.asc(), Person.last_name.asc())
        return list(db.execute(stmt).all())


# Intancia del repositorio inyectando el modelo ORM
user_vehicle_repository = RepositoryUserVehicle(UserVehicle)
