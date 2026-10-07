from app.db.seeds.engine import SeedSpec
from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.product import Product
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.models.coreModule.user_vehicle import UserVehicle
from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.route import Route
from app.models.parametersModule.vehicle import Vehicle
from app.models.parametersModule.zone import Zone
from app.models.securityModule.person import Person
from app.models.securityModule.role import Role
from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
from app.schemas.coreModule.client_route_schema import ClientRouteCreate
from app.schemas.coreModule.client_schema import ClientCreate
from app.schemas.coreModule.product_schema import ProductCreate
from app.schemas.coreModule.special_customer_price_schema import (
    SpecialCustomerPriceCreate,
)
from app.schemas.coreModule.user_vehicle_schema import UserVehicleCreate
from app.schemas.parametersModule.neighborhood_schema import NeighborhoodCreate
from app.schemas.parametersModule.route_schema import RouteCreate
from app.schemas.parametersModule.vehicle_schema import VehicleCreate
from app.schemas.parametersModule.zone_schema import ZoneCreate
from app.schemas.securityModule.person_schema import PersonCreate
from app.schemas.securityModule.role_schema import RoleCreate
from app.schemas.securityModule.user_role_schema import UserRoleCreate
from app.schemas.securityModule.user_schema import UserCreate
from app.utils.helpers.password_helper import hash_password

# El orden de esta tupla ES el orden de dependencias. No lo alteres.
SEEDS: tuple[SeedSpec, ...] = (
    # Nivel 1
    SeedSpec("securityModule/person.jsonc", Person, PersonCreate),
    SeedSpec("securityModule/role.jsonc", Role, RoleCreate),
    SeedSpec("parametersModule/zone.jsonc", Zone, ZoneCreate),
    SeedSpec("parametersModule/vehicle.jsonc", Vehicle, VehicleCreate),
    SeedSpec("parametersModule/route.jsonc", Route, RouteCreate),
    SeedSpec("coreModule/product.jsonc", Product, ProductCreate),
    # Nivel 2
    SeedSpec("parametersModule/neighborhood.jsonc", Neighborhood, NeighborhoodCreate),
    SeedSpec(
        "securityModule/user.jsonc",
        User,
        UserCreate,
        transform=lambda r: {**r, "password": hash_password(r["password"])},
    ),
    # Nivel 3
    SeedSpec("securityModule/user_role.jsonc", UserRole, UserRoleCreate),
    SeedSpec("coreModule/client.jsonc", Client, ClientCreate),
    # Nivel 4
    SeedSpec("coreModule/client_route.jsonc", ClientRoute, ClientRouteCreate),
    SeedSpec("coreModule/user_vehicle.jsonc", UserVehicle, UserVehicleCreate),
    SeedSpec(
        "coreModule/special_customer_price.jsonc",
        SpecialCustomerPrice,
        SpecialCustomerPriceCreate,
    ),
)
