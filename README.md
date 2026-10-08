# Sitema de Toma de Pedidos y Facturacion

## Comandos de Inicialización

Crea Ambiente (Si no se tiene aun)
```bash
py -3.12 -m  venv .venv
```

Instalar depedencias
```bash
pip install -r requirements.txt
```

Aplicar Migración
```bash
alembic upgrade head
```

Ejecutar Seeds
```bash
python -m app.db.seeds
```

Ejecutar API
```bash
uvicorn app.main:app --reload
```

## Comandos Extras

Crear Migracion
```bash
alembic revision --autogenerate -m "Nombre"
```

Truncar Base de Datos
```bash
alembic downgrade base
```

## Pendientes SPFF

- [ ] Refresh token en cookie - Al implementar el front:

Son ajustes concretos, pero no hace falta implementarlos hoy (depende de decisiones que solo se pueden tomar cuando exista el frontend real: dominio, si está en el mismo origen o no, HTTPS, etc.). Te dejo la lista para tu libreta:

- **Dejar de devolver `refresh_token` en el body del JSON.** `Token` (schema) quedaría solo con `access_token` + `token_type`.
- **Enviar el refresh token como cookie `httpOnly` + `Secure`**, usando `Response.set_cookie(...)` en los endpoints `login` y `refresh`. `httpOnly` evita que JavaScript pueda leerlo (mitiga robo por XSS); `Secure` exige HTTPS.
- **`/auth/refresh` debe leer el token desde la cookie**, no desde el body — cambia de recibir `RefreshRequest` a leer `request.cookies.get("refresh_token")`.
- **`/auth/logout` debe limpiar la cookie** (`Response.delete_cookie(...)`) además de revocar la sesión en BD.
- **Configurar CORS con `allow_credentials=True`** y **orígenes explícitos** (no `allow_origins=["*"]"` — los navegadores rechazan cookies con wildcard cuando `credentials` está activo).
- **Decidir `SameSite`**: si el frontend vive en un dominio/puerto distinto al backend (típico en desarrollo, ej. `localhost:3000` → `localhost:8000`), se necesita `SameSite=None` + `Secure=True` (que a su vez exige HTTPS incluso en dev, usualmente vía proxy). Si terminan en el mismo dominio, `SameSite=Lax` basta y es más simple.
- **Limitar el `path` de la cookie** a `/api/v1/auth/refresh` (opcional pero recomendado) — así el navegador solo la envía a ese endpoint específico, no a cada petición de la API.

Ninguno de estos cambios afecta el resto de la arquitectura que ya construiste — solo toca `auth_route.py`, `auth_schema.py` y la configuración de CORS en `main.py`.

---

- [ ] Refresh token en cookie - Al implementar el front: