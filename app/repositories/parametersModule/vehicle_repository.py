from app.models.parametersModule.vehicle import Vehicle
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.vehicle_schema import VehicleCreate, VehicleUpdate


class RepositoryVehicle(BaseRepository[Vehicle, VehicleCreate, VehicleUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
vehicle_repository = RepositoryVehicle(Vehicle)
