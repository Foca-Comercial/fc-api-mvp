# Sistema de Toma de Pedidos y Facturación 🧊

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
# Archivado mensual en Google Sheets (solo necesario para exportar/purgar)
GOOGLE_CREDENTIALS_FILE=credentials/google-service-account.json
HISTORY_RETENTION_MONTHS=2
# Vendedor (user_vehicle.code) que recibe en el cierre los pedidos sin conductor
DEFAULT_SELLER_CODE=01
# Cookie del refresh token. En producción con HTTPS: COOKIE_SECURE=true; si el front
# y la API quedan en dominios distintos: COOKIE_SAMESITE=none (exige Secure)
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
# COOKIE_DOMAIN=
# CORS: solo si el front vive en otro origen (lista JSON). Vacío en desarrollo (proxy)
# CORS_ORIGINS=["https://app.ejemplo.com"]
```

### Google Sheets (archivado mensual)

1. En Google Cloud, crea una **cuenta de servicio**, habilita la API de Google Sheets y
   descarga su llave JSON. Guárdala fuera del control de versiones y apunta
   `GOOGLE_CREDENTIALS_FILE` a esa ruta.
2. Crea un spreadsheet por año y **compártelo como editor** con el `client_email` de la
   cuenta de servicio.
3. Regístralo en el panel de administración (Gestión → Archivo mensual) o en la API:
   `PUT /api/v1/archive/spreadsheets/{año}` con su ID o URL.

### Vendedor por defecto (cierre)

Los seeds lo crean en una BD nueva. En una BD que ya tenía datos, créalo una vez desde el
panel de administración (Gestión → Domiciliarios: un domiciliario con una asignación de
código `01`) o con la API (`POST /users_roles` con el rol `VENDEDOR` y
`POST /users_vehicles` con código `01`). Sin él, el cierre de un día con pedidos sin
conductor responde 422 `DEFAULT_SELLER_MISSING`.

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

## Autenticación (refresh token en cookie)

El refresh token viaja en una cookie `httpOnly` (ruta `/api/v1/auth`) que ponen `login` y
`refresh` y borra `logout`; el body solo trae el access token. En desarrollo el frontend
usa el proxy de `ng serve` (mismo origen), así que no hace falta CORS ni HTTPS. En
producción con dominios distintos: `CORS_ORIGINS` con el origen del frontend,
`COOKIE_SECURE=true` y `COOKIE_SAMESITE=none`. Detalle en `docs/ARQUITECTURA.md`
(sección 8).

> Vinculacion de commits con Discord