from app.models.coreModule.user_vehicle import UserVehicle
from app.repositories.coreModule.user_vehicle_repository import user_vehicle_repository
from app.schemas.coreModule.user_vehicle_schema import (
    UserVehicleCreate,
    UserVehicleUpdate,
)
from app.services.base_service import BaseService


class UserVehicleService(
    BaseService[UserVehicle, UserVehicleCreate, UserVehicleUpdate]
):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(
            repository=user_vehicle_repository, entity_name="UsuarioVehiculo"
        )


# Instancia única para inyectar en el vehicler
user_vehicle_service = UserVehicleService()
