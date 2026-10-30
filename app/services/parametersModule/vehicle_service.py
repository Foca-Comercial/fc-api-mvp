from sqlalchemy.orm import Session

from app.models.parametersModule.vehicle import Vehicle
from app.repositories.parametersModule.vehicle_repository import vehicle_repository
from app.schemas.common.page_schema import Page, PageParams
from app.schemas.parametersModule.vehicle_schema import (
    VehicleAdminFilters,
    VehicleAdminRow,
    VehicleCreate,
    VehicleUpdate,
)
from app.services.base_service import BaseService, UniqueRule
from app.utils.exceptions.business_exceptions import (
    BusinessValidationError,
    EntityNotFoundError,
)

# Campos que un PATCH no puede dejar en null (columnas NOT NULL)
_REQUIRED_ON_UPDATE = {"name": "El nombre", "active": "El estado"}


class VehicleService(BaseService[Vehicle, VehicleCreate, VehicleUpdate]):
    unique_rules = (UniqueRule("name", "Nombre de vehículo"),)

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=vehicle_repository, entity_name="Vehiculo")

    # ------------------------------------------------------------------
    # Panel de administración
    # ------------------------------------------------------------------
    def get_admin_page(
        self, db: Session, *, filters: VehicleAdminFilters, params: PageParams
    ) -> Page[VehicleAdminRow]:
        rows, total = vehicle_repository.get_admin_page(db, filters, params)
        items = [VehicleAdminRow.model_validate(r, from_attributes=True) for r in rows]
        return Page[VehicleAdminRow].build(items, total=total, params=params)

    def create_admin(self, db: Session, *, obj_in: VehicleCreate) -> VehicleAdminRow:
        self._validate_before_create(db, obj_in)  # nombre único
        vehicle = vehicle_repository.add(db, obj_in_data=obj_in.model_dump())
        db.commit()
        return self._admin_row(db, vehicle.id_vehicle)

    def update_admin(
        self, db: Session, *, id_vehicle: int, obj_in: VehicleUpdate
    ) -> VehicleAdminRow:
        """PATCH parcial: nombre y estado. Desactivar un vehículo oculta todas sus
        asignaciones del selector de domiciliarios del pedido (los pedidos que ya
        las tienen las conservan); reactivarlo las vuelve a ofrecer. El nombre se
        puede cambiar siempre: el cierre y Siigo usan el código de la asignación."""
        vehicle = self.get(db, id_vehicle)
        for field, label in _REQUIRED_ON_UPDATE.items():
            if field in obj_in.model_fields_set and getattr(obj_in, field) is None:
                raise BusinessValidationError(
                    f"{label} del vehículo no puede quedar vacío.",
                    field=field,
                    code="REQUIRED_FIELD",
                )
        self._validate_before_update(db, obj_in, vehicle)  # nombre único
        vehicle_repository.update(db, db_obj=vehicle, obj_in=obj_in)
        return self._admin_row(db, id_vehicle)

    @staticmethod
    def _admin_row(db: Session, id_vehicle: int) -> VehicleAdminRow:
        row = vehicle_repository.get_admin_row(db, id_vehicle)
        if row is None:
            raise EntityNotFoundError("Vehiculo", id_vehicle)
        return VehicleAdminRow.model_validate(row, from_attributes=True)


# Instancia única para inyectar en el router
vehicle_service = VehicleService()
