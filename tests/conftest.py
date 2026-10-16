"""
Configuración común de la suite.

- Usa una BD PostgreSQL de pruebas indicada en TEST_DATABASE_URL (nunca la de
  desarrollo). Su nombre debe contener "test", como protección.
- Aplica las migraciones (alembic upgrade head) una vez al iniciar la suite.
- Cada test corre dentro de una transacción que se revierte al terminar: los
  commit() de los services solo liberan un SAVEPOINT, así que la BD queda
  vacía para el siguiente test.
- La autenticación se reemplaza por un usuario de prueba con rol
  GESTOR_COMERCIAL (los roles se prueban aparte, no en estos flujos).
"""

import os
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]

# --- La URL de pruebas debe fijarse ANTES de importar cualquier módulo de app,
#     porque app.core.config lee DATABASE_URL al importarse. ---
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.exit(
        "Define TEST_DATABASE_URL con la BD de pruebas, p. ej. "
        "postgresql+psycopg2://usuario:clave@localhost:5432/fc_db_test",
        returncode=2,
    )
if "test" not in (make_url(TEST_DATABASE_URL).database or "").lower():
    pytest.exit(
        "Por seguridad, el nombre de la BD en TEST_DATABASE_URL debe contener "
        "'test' (los tests escriben y revierten datos en ella).",
        returncode=2,
    )
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "clave-solo-para-tests")
os.environ["DEBUG"] = "false"

from decimal import Decimal
from types import SimpleNamespace

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alembic import command
from app.api.dependencies import CurrentUser, get_current_user
from app.core.config import settings
from app.db.database import engine, get_db
from app.main import app
from app.models.coreModule.client import Client
from app.models.coreModule.product import Product
from app.models.coreModule.user_vehicle import UserVehicle
from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.vehicle import Vehicle
from app.models.parametersModule.zone import Zone
from app.models.securityModule.person import Person
from app.models.securityModule.role import Role
from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
from app.services.coreModule.sheets_writer import get_sheets_writer
from tests.helpers import API, FakeSheetsWriter, item


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    """Deja la BD de pruebas en la última migración antes de correr la suite."""
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture()
def db():
    """Sesión dentro de una transacción externa que se revierte al final."""
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture()
def data(db: Session):
    """Datos mínimos para operar pedidos: zona, barrio, productos, cliente,
    un usuario GESTOR_COMERCIAL (quien toma los pedidos) y un conductor."""
    zone = Zone(name="ZONA TEST", commune_code="Z99")
    db.add(zone)
    db.flush()
    neighborhood = Neighborhood(name="BARRIO TEST", id_zone=zone.id_zone)
    db.add(neighborhood)

    products = [
        Product(code="Z91", name="BOLSA HIELO 2KG", base_price=Decimal("3000.00")),
        Product(code="Z92", name="BOLSA HIELO 5KG", base_price=Decimal("6000.00")),
        Product(code="Z93", name="BOTELLON AGUA", base_price=Decimal("8000.00")),
    ]
    db.add_all(products)

    # Nombres con prefijo de prueba para no chocar si la BD tuviera seeds
    role = Role(name="ROL_TEST_CONDUCTOR")
    db.add(role)

    taker_person = Person(name="Ana", last_name="Gestora")
    driver_person = Person(name="Carlos", last_name="Conductor")
    db.add_all([taker_person, driver_person])
    db.flush()

    taker = User(username="gestor.test", password="x", id_person=taker_person.id_person)
    driver = User(
        username="conductor.test", password="x", id_person=driver_person.id_person
    )
    db.add_all([taker, driver])
    db.flush()

    driver_role = UserRole(id_user=driver.id_user, id_role=role.id_role)
    db.add(driver_role)
    vehicle = Vehicle(name="MOTO TEST")
    db.add(vehicle)
    db.flush()

    user_vehicle = UserVehicle(
        code="99", id_user_role=driver_role.id_user_role, id_vehicle=vehicle.id_vehicle
    )
    client = Client(
        name="CLIENTE REGISTRADO",
        id_neighborhood=neighborhood.id_neighborhood,
        is_registered=True,
    )
    db.add_all([user_vehicle, client])
    # commit = liberar el SAVEPOINT: los datos base quedan en la transacción
    # externa y sobreviven al rollback que hace una petición fallida.
    db.commit()

    return SimpleNamespace(
        neighborhood=neighborhood,
        products=products,
        taker=taker,
        user_vehicle=user_vehicle,
        client=client,
    )


@pytest.fixture()
def client(db: Session, data):
    """TestClient con la sesión de pruebas y el usuario gestor inyectados."""

    def _get_db():
        # Igual que app.db.database.get_db: ante un error se revierte lo pendiente
        # (aquí solo hasta el SAVEPOINT; la transacción externa sigue abierta).
        try:
            yield db
        except Exception:
            db.rollback()
            raise

    def _current_user():
        return CurrentUser(user=data.taker, roles=["GESTOR_COMERCIAL"])

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = _current_user
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def create_order(client: TestClient, data):
    """Crea un pedido para el cliente registrado y devuelve el JSON de respuesta."""

    def _create(items: list[dict] | None = None, **extra) -> dict:
        body = {
            "id_client": data.client.id_client,
            "items": items or [item(data.products[0], 2)],
            **extra,
        }
        response = client.post(f"{API}/orders/existing-client", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture()
def default_seller(db: Session, data, monkeypatch):
    """Vendedor por defecto del cierre (código "09" -> Siigo 9). Recibe los
    pedidos despachados sin conductor."""
    role = Role(name="ROL_TEST_VENDEDOR")
    person = Person(name="Hielo", last_name="Foca")
    db.add_all([role, person])
    db.flush()
    user = User(username="vendedor.test", password="x", id_person=person.id_person)
    db.add(user)
    db.flush()
    user_role = UserRole(id_user=user.id_user, id_role=role.id_role)
    db.add(user_role)
    db.flush()
    seller = UserVehicle(
        code="09",
        id_user_role=user_role.id_user_role,
        id_vehicle=data.user_vehicle.id_vehicle,
    )
    db.add(seller)
    db.commit()
    monkeypatch.setattr(settings, "DEFAULT_SELLER_CODE", "09")
    return seller


@pytest.fixture()
def writer(client):
    """Reemplaza el escritor de Google Sheets por uno en memoria."""
    fake = FakeSheetsWriter()
    app.dependency_overrides[get_sheets_writer] = lambda: fake
    return fake


@pytest.fixture()
def admin(client, data, writer):
    """El mismo TestClient, autenticado como ADMINISTRADOR."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user=data.taker, roles=["ADMINISTRADOR"]
    )
    return client
