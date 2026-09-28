from fastapi import FastAPI

from app.api.routers.securityModule import person_router

app = FastAPI(
    title="FC API MVP",
    description="API para gestión comercial - Foca Comercial",
    version="0.1.0",
)

# Registro de Routers

# SecurityModule
app.include_router(person_router.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "API funcionando correctamente"}
