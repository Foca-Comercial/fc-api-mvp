from app.models.parametersModule.route import Route
from app.repositories.parametersModule.route_repository import route_repository
from app.schemas.parametersModule.route_schema import RouteCreate, RouteUpdate
from app.services.base_service import BaseService, UniqueRule


class RouteService(BaseService[Route, RouteCreate, RouteUpdate]):
    unique_rules = (UniqueRule("name", "Nombre de ruta"),)

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=route_repository, entity_name="Ruta")


# Instancia única para inyectar en el router
route_service = RouteService()
