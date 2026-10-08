from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.special_customer_price_schema import (
    SpecialCustomerPriceCreate,
    SpecialCustomerPriceResponse,
    SpecialCustomerPriceUpdate,
)
from app.services.coreModule.special_customer_price_service import (
    special_customer_price_service,
)

router = SecuredRouter(
    prefix="/specials_customers_prices", tags=["SpecialsCustomersPrices"]
)


@router.get("/", response_model=list[SpecialCustomerPriceResponse])
def get_all_specials_customers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),  # noqa: B008
):
    return special_customer_price_service.get_all(db, skip=skip, limit=limit)


@router.get("/{special_customer_price_id}", response_model=SpecialCustomerPriceResponse)
def get_special(special_customer_price_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return special_customer_price_service.get(db, id=special_customer_price_id)


@router.post(
    "/",
    response_model=SpecialCustomerPriceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_special(
    special_customer_price_in: SpecialCustomerPriceCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return special_customer_price_service.create(db, obj_in=special_customer_price_in)


@router.patch(
    "/{special_customer_price_id}", response_model=SpecialCustomerPriceResponse
)
def update_special(
    special_customer_price_id: int,
    special_customer_price_in: SpecialCustomerPriceUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return special_customer_price_service.update(
        db, id=special_customer_price_id, obj_in=special_customer_price_in
    )


@router.delete("/{special_customer_price_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_special(special_customer_price_id: int, db: Session = Depends(get_db)):  # noqa: B008
    special_customer_price_service.remove(db, id=special_customer_price_id)
