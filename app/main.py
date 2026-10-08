from fastapi import FastAPI

from app.api.exception_handlers import register_exception_handlers
from app.api.routers.auth import auth_router
from app.api.routers.coreModule import (
    client_route_router,
    client_router,
    order_detail_router,
    order_router,
    product_router,
    shift_closure_router,
    special_customer_price_router,
    user_vehicle_router,
)
from app.api.routers.parametersModule import (
    neighborhood_router,
    route_router,
    vehicle_router,
    zone_router,
)
from app.api.routers.securityModule import (
    person_router,
    role_router,
    user_role_router,
    user_router,
)

app = FastAPI(
    title="FC API MVP",
    description="API para gestión comercial - Foca Comercial",
    version="0.1.0",
)

# Registro de Routers

# SecurityModule
app.include_router(person_router.router, prefix="/api/v1")
app.include_router(user_router.router, prefix="/api/v1")
app.include_router(role_router.router, prefix="/api/v1")
app.include_router(user_role_router.router, prefix="/api/v1")

# ParametersModule
app.include_router(zone_router.router, prefix="/api/v1")
app.include_router(neighborhood_router.router, prefix="/api/v1")
app.include_router(route_router.router, prefix="/api/v1")
app.include_router(vehicle_router.router, prefix="/api/v1")

# CoreModule
app.include_router(client_router.router, prefix="/api/v1")
app.include_router(product_router.router, prefix="/api/v1")
app.include_router(special_customer_price_router.router, prefix="/api/v1")
app.include_router(order_router.router, prefix="/api/v1")
app.include_router(order_detail_router.router, prefix="/api/v1")
app.include_router(user_vehicle_router.router, prefix="/api/v1")
app.include_router(shift_closure_router.router, prefix="/api/v1")
app.include_router(client_route_router.router, prefix="/api/v1")

# Registro de Excepciones
register_exception_handlers(app)

# Auth
app.include_router(auth_router.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "API funcionando correctamente"}
