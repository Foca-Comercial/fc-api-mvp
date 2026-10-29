from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.zone import Zone
from app.repositories.base_repository import BaseRepository
from app.repositories.pagination import paginate
from app.schemas.common.page_schema import PageParams
from app.schemas.coreModule.client_schema import (
    ClientAdminFilters,
    ClientCreate,
    ClientUpdate,
)


class RepositoryClient(BaseRepository[Client, ClientCreate, ClientUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Client]:
        stmt = select(self.model)

        if only_active:
            stmt = stmt.where(self.model.active.is_(True))

        stmt = (
            stmt.order_by(*[col.asc() for col in self._primary_key_columns])
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    # Buscar un cliente por su nombre
    def search_by_name(
        self, db: Session, *, name: str, limit: int = 10
    ) -> list[Client]:
        stmt = (
            select(Client)
            .where(
                Client.name.ilike(f"%{name}%"),
                Client.active.is_(True),
                Client.is_registered.is_(True),
            )
            .order_by(Client.name)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Panel de administración: clientes registrados
    # ------------------------------------------------------------------
    @staticmethod
    def _admin_conditions(filters: ClientAdminFilters) -> list[Any]:
        conditions: list[Any] = [Client.is_registered.is_(True)]
        if filters.search:
            # autoescape: un "%" o "_" escrito por el usuario se busca literal
            conditions.append(
                or_(
                    Client.name.icontains(filters.search, autoescape=True),
                    Client.phone.startswith(filters.search, autoescape=True),
                )
            )
        if filters.active is not None:
            conditions.append(Client.active.is_(filters.active))
        if filters.id_zone is not None:
            conditions.append(Neighborhood.id_zone == filters.id_zone)
        return conditions

    @staticmethod
    def _admin_select() -> Select:
        """Fila del listado: cliente + barrio + zona + conteos. Los conteos son
        subconsultas correlacionadas: solo se calculan para las filas de la página."""
        special_prices = (
            select(func.count(SpecialCustomerPrice.id_client_price))
            .where(SpecialCustomerPrice.id_client == Client.id_client)
            .correlate(Client)
            .scalar_subquery()
        )
        routes = (
            select(func.count(ClientRoute.id_client_route))
            .where(ClientRoute.id_client == Client.id_client)
            .correlate(Client)
            .scalar_subquery()
        )
        return (
            select(
                Client.id_client,
                Client.name,
                Client.phone,
                Client.address,
                Client.id_neighborhood,
                Neighborhood.name.label("neighborhood_name"),
                Zone.id_zone,
                Zone.name.label("zone_name"),
                Client.active,
                special_prices.label("special_prices_count"),
                routes.label("routes_count"),
            )
            .join(Neighborhood, Neighborhood.id_neighborhood == Client.id_neighborhood)
            .join(Zone, Zone.id_zone == Neighborhood.id_zone)
        )

    # Una página de clientes registrados, por nombre (A-Z)
    def get_admin_page(
        self, db: Session, filters: ClientAdminFilters, params: PageParams
    ) -> tuple[list[Any], int]:
        conditions = self._admin_conditions(filters)
        stmt = (
            self._admin_select()
            .where(*conditions)
            .order_by(Client.name, Client.id_client)
        )
        # El conteo no necesita la zona ni las subconsultas
        count_stmt = (
            select(Client.id_client)
            .join(Neighborhood, Neighborhood.id_neighborhood == Client.id_neighborhood)
            .where(*conditions)
        )
        return paginate(db, stmt, params, count_stmt=count_stmt)

    # La misma fila del listado para un cliente (respuesta de crear/editar)
    def get_admin_row(self, db: Session, id_client: int) -> Any | None:
        stmt = self._admin_select().where(Client.id_client == id_client)
        return db.execute(stmt).one_or_none()


# Intancia del repositorio inyectando el modelo ORM
client_repository = RepositoryClient(Client)
