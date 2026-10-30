from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_page_params
from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.common.page_schema import Page, PageParams
from app.schemas.parametersModule.vehicle_schema import (
    VehicleAdminFilters,
    VehicleAdminRow,
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
)
from app.services.parametersModule.vehicle_service import vehicle_service
from app.utils.enums.delete_type import DeletionType

router = SecuredRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("/", response_model=list[VehicleResponse])
def get_all_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return vehicle_service.get_all(db, skip=skip, limit=limit)


# -----------------------------------------------------
# Panel de administración (solo ADMINISTRADOR). Literales: antes de /{vehicle_id}
# -----------------------------------------------------
@router.get("/admin", response_model=Page[VehicleAdminRow])
def list_vehicles_admin(
    search: str | None = Query(
        None, min_length=1, max_length=50, description="Nombre (contiene)"
    ),
    active: bool | None = Query(None, description="Sin valor: activos e inactivos"),
    params: PageParams = Depends(get_page_params),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    filters = VehicleAdminFilters(
        search=search.strip() if search and search.strip() else None, active=active
    )
    return vehicle_service.get_admin_page(db, filters=filters, params=params)


@router.post(
    "/admin", response_model=VehicleAdminRow, status_code=status.HTTP_201_CREATED
)
def create_vehicle_admin(vehicle_in: VehicleCreate, db: Session = Depends(get_db)):  # noqa: B008
    return vehicle_service.create_admin(db, obj_in=vehicle_in)


# Editar, desactivar ({"active": false}) o reactivar ({"active": true})
@router.patch("/admin/{vehicle_id}", response_model=VehicleAdminRow)
def update_vehicle_admin(
    vehicle_id: int,
    vehicle_in: VehicleUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return vehicle_service.update_admin(db, id_vehicle=vehicle_id, obj_in=vehicle_in)


# -----------------------------------------------------
# CRUD genérico (ADMINISTRADOR)
# -----------------------------------------------------
@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return vehicle_service.get(db, id=vehicle_id)


@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(vehicle_in: VehicleCreate, db: Session = Depends(get_db)):  # noqa: B008
    return vehicle_service.create(db, obj_in=vehicle_in)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: int,
    vehicle_in: VehicleUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return vehicle_service.update(db, id=vehicle_id, obj_in=vehicle_in)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return vehicle_service.remove(db, id=vehicle_id, strategy_type=strategy)
