from sqlalchemy.orm import Session

from app.models.coreModule.user_vehicle import UserVehicle
from app.repositories.coreModule.user_vehicle_repository import user_vehicle_repository
from app.schemas.coreModule.user_vehicle_schema import (
    DriverVehicleDropdownResponse,
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

    # Listado de las asignaciones Conductor-Vehiculo ordenado por nombre conductor
    def list_drivers_for_assignment(
        self, db: Session
    ) -> list[DriverVehicleDropdownResponse]:
        results = self.repository.get_all_ordered_by_driver_name(db)
        return [
            DriverVehicleDropdownResponse(
                id_user_vehicle=row.id_user_vehicle,
                code=row.code,
                driver_name=row.driver_name,
                vehicle_name=row.vehicle_name,
            )
            for row in results
        ]


# Instancia única para inyectar en el vehicler
user_vehicle_service = UserVehicleService()
