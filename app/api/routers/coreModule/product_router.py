from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_page_params
from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.common.page_schema import Page, PageParams
from app.schemas.coreModule.product_schema import (
    ProductAdminFilters,
    ProductAdminRow,
    ProductCatalogItem,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.coreModule.product_service import product_service
from app.utils.enums.delete_type import DeletionType

router = SecuredRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductResponse])
def get_all_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return product_service.get_all(db, skip=skip, limit=limit)


# Obtener listado de productos con sus precios (id_client para precios especiales)
@router.get(
    "/catalog", response_model=list[ProductCatalogItem], roles=["GESTOR_COMERCIAL"]
)
def get_catalog(id_client: int | None = Query(None), db: Session = Depends(get_db)):  # noqa: B008
    return product_service.get_catalog(db, id_client=id_client)


# -----------------------------------------------------
# Panel de administración (solo ADMINISTRADOR). Literales: antes de /{product_id}
# -----------------------------------------------------
@router.get("/admin", response_model=Page[ProductAdminRow])
def list_products_admin(
    search: str | None = Query(
        None,
        min_length=1,
        max_length=50,
        description="Código (empieza por) o nombre (contiene)",
    ),
    active: bool | None = Query(None, description="Sin valor: activos e inactivos"),
    params: PageParams = Depends(get_page_params),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    filters = ProductAdminFilters(
        search=search.strip() if search and search.strip() else None, active=active
    )
    return product_service.get_admin_page(db, filters=filters, params=params)


@router.post(
    "/admin", response_model=ProductAdminRow, status_code=status.HTTP_201_CREATED
)
def create_product_admin(product_in: ProductCreate, db: Session = Depends(get_db)):  # noqa: B008
    return product_service.create_admin(db, obj_in=product_in)


# Editar, desactivar ({"active": false}) o reactivar ({"active": true})
@router.patch("/admin/{product_id}", response_model=ProductAdminRow)
def update_product_admin(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return product_service.update_admin(db, id_product=product_id, obj_in=product_in)


# -----------------------------------------------------
# CRUD genérico (ADMINISTRADOR)
# -----------------------------------------------------
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return product_service.get(db, id=product_id)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):  # noqa: B008
    return product_service.create(db, obj_in=product_in)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return product_service.update(db, id=product_id, obj_in=product_in)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return product_service.remove(db, id=product_id, strategy_type=strategy)
