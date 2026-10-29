from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_page_params
from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.common.page_schema import Page, PageParams
from app.schemas.coreModule.driver_schema import (
    DriverAdminFilters,
    DriverAdminRow,
    DriverAssignmentCreate,
    DriverAssignmentRow,
    DriverAssignmentUpdate,
    DriverCreate,
    DriverUpdate,
    NextSellerCode,
)
from app.services.coreModule.driver_service import driver_service

# Panel de administración: domiciliarios (usuarios con rol VENDEDOR) y sus
# asignaciones con vehículos. Solo ADMINISTRADOR (rol por defecto de SecuredRouter).
router = SecuredRouter(prefix="/drivers", tags=["Drivers"])


@router.get("/admin", response_model=Page[DriverAdminRow])
def list_drivers_admin(
    search: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Nombre o apellido (contiene) o código (empieza por)",
    ),
    active: bool | None = Query(None, description="Sin valor: activos e inactivos"),
    params: PageParams = Depends(get_page_params),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    filters = DriverAdminFilters(
        search=search.strip() if search and search.strip() else None, active=active
    )
    return driver_service.get_admin_page(db, filters=filters, params=params)


# Sugerencia de código para una asignación nueva. Literal: antes de /admin/{user_id}
@router.get("/admin/next-code", response_model=NextSellerCode)
def get_next_seller_code(db: Session = Depends(get_db)):  # noqa: B008
    return driver_service.next_code(db)


# Crea persona + usuario (nombre.apellido) + rol VENDEDOR en una transacción
@router.post(
    "/admin", response_model=DriverAdminRow, status_code=status.HTTP_201_CREATED
)
def create_driver(driver_in: DriverCreate, db: Session = Depends(get_db)):  # noqa: B008
    return driver_service.create(db, obj_in=driver_in)


# Editar datos, desactivar ({"active": false}) o reactivar ({"active": true})
@router.patch("/admin/{user_id}", response_model=DriverAdminRow)
def update_driver(
    user_id: int,
    driver_in: DriverUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return driver_service.update(db, id_user=user_id, obj_in=driver_in)


# --- Asignaciones domiciliario + vehículo (código de vendedor) ---


@router.get(
    "/admin/{user_id}/assignments", response_model=list[DriverAssignmentRow]
)
def list_driver_assignments(user_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return driver_service.list_assignments(db, id_user=user_id)


@router.post(
    "/admin/{user_id}/assignments",
    response_model=DriverAssignmentRow,
    status_code=status.HTTP_201_CREATED,
)
def create_driver_assignment(
    user_id: int,
    body: DriverAssignmentCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return driver_service.create_assignment(db, id_user=user_id, obj_in=body)


# Código, vehículo o estado. Con pedidos o cierres solo cambia el estado.
@router.patch(
    "/admin/{user_id}/assignments/{user_vehicle_id}",
    response_model=DriverAssignmentRow,
)
def update_driver_assignment(
    user_id: int,
    user_vehicle_id: int,
    body: DriverAssignmentUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return driver_service.update_assignment(
        db, id_user=user_id, id_user_vehicle=user_vehicle_id, obj_in=body
    )


# Solo una asignación que nunca se usó (sin pedidos ni cierres)
@router.delete(
    "/admin/{user_id}/assignments/{user_vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_driver_assignment(
    user_id: int,
    user_vehicle_id: int,
    db: Session = Depends(get_db),  # noqa: B008
):
    driver_service.delete_assignment(
        db, id_user=user_id, id_user_vehicle=user_vehicle_id
    )
