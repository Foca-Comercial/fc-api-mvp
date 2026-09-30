from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.parametersModule.route_schema import (
    RouteCreate,
    RouteResponse,
    RouteUpdate,
)
from app.services.parametersModule.route_service import route_service

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get("/", response_model=list[RouteResponse])
def get_all_routes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return route_service.get_all(db, skip=skip, limit=limit)


@router.get("/{route_id}", response_model=RouteResponse)
def get_route(route_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return route_service.get(db, id=route_id)


@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def create_route(route_in: RouteCreate, db: Session = Depends(get_db)):  # noqa: B008
    return route_service.create(db, obj_in=route_in)


@router.patch("/{route_id}", response_model=RouteResponse)
def update_route(
    route_id: int,
    route_in: RouteUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return route_service.update(db, id=route_id, obj_in=route_in)


@router.delete("/{route_id}", response_model=RouteResponse)
def delete_route(route_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return route_service.remove(db, id=route_id)
