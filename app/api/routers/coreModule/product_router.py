from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.product_schema import (
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


@router.get(
    "/catalog", response_model=list[ProductCatalogItem], roles=["GESTOR_COMERCIAL"]
)
def get_catalog(id_client: int | None = Query(None), db: Session = Depends(get_db)):  # noqa: B008
    return product_service.get_catalog(db, id_client=id_client)


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
