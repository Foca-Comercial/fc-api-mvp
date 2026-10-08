from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parametersModule.vehicle import Vehicle
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.vehicle_schema import VehicleCreate, VehicleUpdate


class RepositoryVehicle(BaseRepository[Vehicle, VehicleCreate, VehicleUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Vehicle]:
        stmt = select(self.model)

        if only_active:
            stmt = stmt.where(self.model.active.is_(True))

        stmt = (
            stmt.order_by(*[col.asc() for col in self._primary_key_columns])
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())


# Intancia del repositorio inyectando el modelo ORM
vehicle_repository = RepositoryVehicle(Vehicle)
