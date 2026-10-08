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

### Solar System Exploration, 1950s – 1960s

- [ ] Mercury
- [x] Venus
- [x] Earth (Orbit/Moon)
- [x] Mars
- [ ] Jupiter
- [ ] Saturn
- [ ] Uranus
- [ ] Neptune
- [ ] Comet Haley