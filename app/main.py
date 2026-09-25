from fastapi import FastAPI

app = FastAPI(
    title="FC API MVP",
    description="API para gestión comercial - Foca Comercial",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "API funcionando correctamente"}
