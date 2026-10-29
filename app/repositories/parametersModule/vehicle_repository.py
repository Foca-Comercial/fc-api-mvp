from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.coreModule.user_vehicle import UserVehicle
from app.models.parametersModule.vehicle import Vehicle
from app.repositories.base_repository import BaseRepository
from app.repositories.pagination import paginate
from app.schemas.common.page_schema import PageParams
from app.schemas.parametersModule.vehicle_schema import (
    VehicleAdminFilters,
    VehicleCreate,
    VehicleUpdate,
)


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

    # ------------------------------------------------------------------
    # Panel de administración
    # ------------------------------------------------------------------
    @staticmethod
    def _admin_conditions(filters: VehicleAdminFilters) -> list[Any]:
        conditions: list[Any] = []
        if filters.search:
            conditions.append(Vehicle.name.icontains(filters.search, autoescape=True))
        if filters.active is not None:
            conditions.append(Vehicle.active.is_(filters.active))
        return conditions

    @staticmethod
    def _admin_select() -> Select:
        assignments = (
            select(func.count(UserVehicle.id_user_vehicle))
            .where(
                UserVehicle.id_vehicle == Vehicle.id_vehicle,
                UserVehicle.active.is_(True),
            )
            .correlate(Vehicle)
            .scalar_subquery()
        )
        return select(
            Vehicle.id_vehicle,
            Vehicle.name,
            Vehicle.active,
            assignments.label("assignments_count"),
        )

    # Una página de vehículos, por nombre
    def get_admin_page(
        self, db: Session, filters: VehicleAdminFilters, params: PageParams
    ) -> tuple[list[Any], int]:
        conditions = self._admin_conditions(filters)
        stmt = (
            self._admin_select()
            .where(*conditions)
            .order_by(Vehicle.name, Vehicle.id_vehicle)
        )
        count_stmt = select(Vehicle.id_vehicle).where(*conditions)
        return paginate(db, stmt, params, count_stmt=count_stmt)

    def get_admin_row(self, db: Session, id_vehicle: int) -> Any | None:
        stmt = self._admin_select().where(Vehicle.id_vehicle == id_vehicle)
        return db.execute(stmt).one_or_none()


# Intancia del repositorio inyectando el modelo ORM
vehicle_repository = RepositoryVehicle(Vehicle)
