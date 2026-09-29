from app.models.parametersModule.vehicle import Vehicle
from app.repositories.parametersModule.vehicle_repository import vehicle_repository
from app.schemas.parametersModule.vehicle_schema import VehicleCreate, VehicleUpdate
from app.services.base_service import BaseService


class VehicleService(BaseService[Vehicle, VehicleCreate, VehicleUpdate]):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=vehicle_repository, entity_name="Vehiculo")


# Instancia única para inyectar en el router
vehicle_service = VehicleService()
