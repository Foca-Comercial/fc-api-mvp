from app.models.coreModule.user_vehicle import UserVehicle
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.user_vehicle_schema import (
    UserVehicleCreate,
    UserVehicleUpdate,
)


class RepositoryUserVehicle(
    BaseRepository[UserVehicle, UserVehicleCreate, UserVehicleUpdate]
):
    pass


# Intancia del repositorio inyectando el modelo ORM
user_vehicle_repository = RepositoryUserVehicle(UserVehicle)
