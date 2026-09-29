from app.models.parametersModule.zone import Zone
from app.repositories.parametersModule.zone_repository import zone_repository
from app.schemas.parametersModule.zone_schema import ZoneCreate, ZoneUpdate
from app.services.base_service import BaseService


class ZoneService(BaseService[Zone, ZoneCreate, ZoneUpdate]):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=zone_repository, entity_name="Zons")


# Instancia única para inyectar en el router
zone_service = ZoneService()
