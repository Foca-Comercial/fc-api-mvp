from app.models.parametersModule.zone import Zone
from app.repositories.parametersModule.zone_repository import zone_repository
from app.schemas.parametersModule.zone_schema import ZoneCreate, ZoneUpdate
from app.services.base_service import BaseService, UniqueRule


class ZoneService(BaseService[Zone, ZoneCreate, ZoneUpdate]):
    unique_rules = (
        UniqueRule("name", "Nombre de zona"),
        UniqueRule("commune_code", "Código de comuna"),
    )

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=zone_repository, entity_name="Zona")


# Instancia única para inyectar en el router
zone_service = ZoneService()
