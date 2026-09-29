from app.models.parametersModule.zone import Zone
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.zone_schema import ZoneCreate, ZoneUpdate


class RepositoryZone(BaseRepository[Zone, ZoneCreate, ZoneUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
zone_repository = RepositoryZone(Zone)
