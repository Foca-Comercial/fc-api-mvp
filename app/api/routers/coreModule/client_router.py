from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_page_params
from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.common.page_schema import Page, PageParams
from app.schemas.coreModule.client_schema import (
    ClientAdminCreate,
    ClientAdminFilters,
    ClientAdminRow,
    ClientAdminUpdate,
    ClientCreate,
    ClientResponse,
    ClientUpdate,
)
from app.schemas.coreModule.special_customer_price_schema import (
    ClientSpecialPriceRow,
    ClientSpecialPriceSet,
)
from app.services.coreModule.client_service import client_service
from app.services.coreModule.special_customer_price_service import (
    special_customer_price_service,
)
from app.utils.enums.delete_type import DeletionType

router = SecuredRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=list[ClientResponse])
def get_all_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.get_all(db, skip=skip, limit=limit)


# Buscar cliente por su nombre
@router.get("/search", response_model=list[ClientResponse], roles=["GESTOR_COMERCIAL"])
def search_clients(name: str = Query(..., min_length=2), db: Session = Depends(get_db)):  # noqa: B008
    return client_service.search_by_name(db, name=name)


# -----------------------------------------------------
# Panel de administración (solo ADMINISTRADOR): clientes REGISTRADOS.
# Literales: antes de /{client_id}
# -----------------------------------------------------
@router.get("/admin", response_model=Page[ClientAdminRow])
def list_clients_admin(
    search: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Nombre (contiene) o teléfono (empieza por)",
    ),
    active: bool | None = Query(None, description="Sin valor: activos e inactivos"),
    id_zone: int | None = Query(None, gt=0),
    params: PageParams = Depends(get_page_params),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    filters = ClientAdminFilters(
        search=search.strip() if search and search.strip() else None,
        active=active,
        id_zone=id_zone,
    )
    return client_service.get_admin_page(db, filters=filters, params=params)


@router.post(
    "/admin", response_model=ClientAdminRow, status_code=status.HTTP_201_CREATED
)
def create_client_admin(client_in: ClientAdminCreate, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.create_registered(db, obj_in=client_in)


# Editar, desactivar ({"active": false}) o reactivar ({"active": true})
@router.patch("/admin/{client_id}", response_model=ClientAdminRow)
def update_client_admin(
    client_id: int,
    client_in: ClientAdminUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return client_service.update_registered(db, id_client=client_id, obj_in=client_in)


# --- Precios especiales del cliente (uno por producto) ---


@router.get(
    "/admin/{client_id}/special-prices", response_model=list[ClientSpecialPriceRow]
)
def list_client_special_prices(client_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return special_customer_price_service.list_for_client(db, id_client=client_id)


# Asigna o cambia el precio pactado del producto (idempotente)
@router.put(
    "/admin/{client_id}/special-prices/{product_id}",
    response_model=ClientSpecialPriceRow,
)
def set_client_special_price(
    client_id: int,
    product_id: int,
    body: ClientSpecialPriceSet,
    db: Session = Depends(get_db),  # noqa: B008
):
    return special_customer_price_service.set_for_client(
        db, id_client=client_id, id_product=product_id, obj_in=body
    )


@router.delete(
    "/admin/{client_id}/special-prices/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_client_special_price(
    client_id: int,
    product_id: int,
    db: Session = Depends(get_db),  # noqa: B008
):
    special_customer_price_service.remove_for_client(
        db, id_client=client_id, id_product=product_id
    )


# -----------------------------------------------------
# CRUD genérico (ADMINISTRADOR)
# -----------------------------------------------------
@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.get(db, id=client_id)


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(client_in: ClientCreate, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.create(db, obj_in=client_in)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return client_service.update(db, id=client_id, obj_in=client_in)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return client_service.remove(db, id=client_id, strategy_type=strategy)
