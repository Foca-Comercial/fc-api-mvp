# Sistema de Toma de Pedidos y Facturación

API REST de **Foca Comercial** (FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL).
La documentación técnica (arquitectura, convenciones, flujos de negocio y roadmap) está en
[`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md).

## Configuración (`.env`)

Crea un archivo `.env` en la **raíz del proyecto** (no se versiona):

```env
# Formato: postgresql+psycopg2://usuario:contraseña@servidor:puerto/nombre_bd
DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/fc_db
SECRET_KEY=<generar con: python -c "import secrets; print(secrets.token_hex(32))">
DEBUG=false
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
```

## Comandos de Inicialización

Crear ambiente (si no se tiene aún)
```bash
py -3.12 -m  venv .venv
```

Instalar dependencias
```bash
pip install -r requirements.txt
```

Aplicar migraciones
```bash
alembic upgrade head
```

Ejecutar seeds (solo llena tablas vacías; ver `docs/ARQUITECTURA.md`, sección 6)
```bash
python -m app.db.seeds
```

Ejecutar API
```bash
uvicorn app.main:app --reload
```

## Pruebas

Requieren una base de datos PostgreSQL **aparte**, vacía, cuyo nombre contenga `test`
(por ejemplo `fc_db_test`). La suite le aplica las migraciones sola y deja cada test en
una transacción que se revierte, así que no hace falta cargarle seeds.

```bash
pip install -r requirements-dev.txt
```

PowerShell:
```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg2://usuario:clave@localhost:5432/fc_db_test"
pytest
```

Bash:
```bash
TEST_DATABASE_URL="postgresql+psycopg2://usuario:clave@localhost:5432/fc_db_test" pytest
```

## Comandos Extras

Crear migración (revisar el archivo generado antes de aplicarlo)
```bash
alembic revision --autogenerate -m "Nombre"
```

Revertir todas las migraciones (elimina las tablas y sus datos)
```bash
alembic downgrade base
```

## Pendientes SPFF

- [ ] Refresh token en cookie - Al implementar el front:

Son ajustes concretos, pero no hace falta implementarlos hoy (depende de decisiones que solo se pueden tomar cuando exista el frontend real: dominio, si está en el mismo origen o no, HTTPS, etc.). Lista de cambios:

- **Dejar de devolver `refresh_token` en el body del JSON.** `Token` (schema) quedaría solo con `access_token` + `token_type`.
- **Enviar el refresh token como cookie `httpOnly` + `Secure`**, usando `Response.set_cookie(...)` en los endpoints `login` y `refresh`. `httpOnly` evita que JavaScript pueda leerlo (mitiga robo por XSS); `Secure` exige HTTPS.
- **`/auth/refresh` debe leer el token desde la cookie**, no desde el body — cambia de recibir `RefreshRequest` a leer `request.cookies.get("refresh_token")`.
- **`/auth/logout` debe limpiar la cookie** (`Response.delete_cookie(...)`) además de revocar la sesión en BD.
- **Configurar CORS con `allow_credentials=True`** y **orígenes explícitos** (no `allow_origins=["*"]` — los navegadores rechazan cookies con wildcard cuando `credentials` está activo).
- **Decidir `SameSite`**: si el frontend vive en un dominio/puerto distinto al backend (típico en desarrollo, ej. `localhost:3000` → `localhost:8000`), se necesita `SameSite=None` + `Secure=True` (que a su vez exige HTTPS incluso en dev, usualmente vía proxy). Si terminan en el mismo dominio, `SameSite=Lax` basta y es más simple.
- **Limitar el `path` de la cookie** a `/api/v1/auth/refresh` (opcional pero recomendado) — así el navegador solo la envía a ese endpoint específico, no a cada petición de la API.

Ninguno de estos cambios afecta el resto de la arquitectura ya construida — solo toca `auth_router.py`, `auth_schema.py` y la configuración de CORS en `main.py`.
