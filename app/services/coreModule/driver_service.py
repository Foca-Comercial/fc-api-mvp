"""Panel de administración: domiciliarios y sus asignaciones con vehículos.

Un domiciliario es Person + User + UserRole (VENDEDOR); se crea en una sola
transacción con usuario "nombre.apellido" (sufijo si ya existe) y la contraseña
inicial de la data inicial (hoy el VENDEDOR no inicia sesión; se cambiará cuando
exista la app del domiciliario).

Cada asignación (`user_vehicle`) es la pareja domiciliario + vehículo con su código
de vendedor para Siigo. Reglas:
- El código (2 dígitos) es único. Una asignación con pedidos o cierres no cambia de
  código ni de vehículo: el cierre y Siigo usan el código actual. Se desactiva y se
  crea otra.
- No se borra si tiene pedidos o cierres (se desactiva).
- La del vendedor por defecto (DEFAULT_SELLER_CODE) no se desactiva, cambia ni borra:
  el cierre le suma los pedidos sin conductor.
- Un domiciliario con otro rol (p. ej. ADMINISTRADOR) o dueño del vendedor por
  defecto no se desactiva desde aquí.
"""

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.coreModule.user_vehicle import UserVehicle
from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
from app.repositories.coreModule.driver_repository import driver_repository
from app.repositories.coreModule.user_vehicle_repository import (
    user_vehicle_repository,
)
from app.repositories.parametersModule.vehicle_repository import vehicle_repository
from app.repositories.securityModule.person_repository import person_repository
from app.repositories.securityModule.user_repository import user_repository
from app.repositories.securityModule.user_role_repository import (
    user_role_repository,
)
from app.schemas.common.page_schema import Page, PageParams
from app.schemas.coreModule.driver_schema import (
    DriverAdminFilters,
    DriverAdminRow,
    DriverAssignmentCreate,
    DriverAssignmentRow,
    DriverAssignmentUpdate,
    DriverCreate,
    DriverUpdate,
    NextSellerCode,
)
from app.services.validation import ensure_reference
from app.utils.exceptions.business_exceptions import (
    BusinessRuleViolationError,
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
)
from app.utils.helpers.password_helper import hash_password
from app.utils.helpers.string_helper import username_base

# Contraseña inicial, la misma de la data inicial (decisión del negocio: el
# VENDEDOR aún no inicia sesión). Se cambiará al construir la app del domiciliario.
INITIAL_PASSWORD = "contrasena"

_PERSON_FIELDS = ("name", "last_name", "phone", "email")
# Campos que un PATCH no puede dejar en null (columnas NOT NULL)
_REQUIRED_DRIVER = {
    "name": "El nombre del domiciliario",
    "last_name": "El apellido del domiciliario",
    "active": "El estado del domiciliario",
}
_REQUIRED_ASSIGNMENT = {
    "code": "El código de la asignación",
    "id_vehicle": "El vehículo de la asignación",
    "active": "El estado de la asignación",
}


class DriverService:
    # ------------------------------------------------------------------
    # Domiciliarios
    # ------------------------------------------------------------------
    def get_admin_page(
        self, db: Session, *, filters: DriverAdminFilters, params: PageParams
    ) -> Page[DriverAdminRow]:
        rows, total = driver_repository.get_admin_page(db, filters, params)
        items = [DriverAdminRow.model_validate(r, from_attributes=True) for r in rows]
        return Page[DriverAdminRow].build(items, total=total, params=params)

    def create(self, db: Session, *, obj_in: DriverCreate) -> DriverAdminRow:
        id_role = driver_repository.get_role_id(db)
        if id_role is None:
            raise BusinessRuleViolationError(
                "No existe el rol VENDEDOR. Créalo en /roles para registrar "
                "domiciliarios.",
                rule_code="SELLER_ROLE_MISSING",
            )
        # Persona + usuario + rol en una sola transacción (flush, un único commit)
        person = person_repository.add(
            db, obj_in_data={**obj_in.model_dump(), "active": True}
        )
        user = user_repository.add(
            db,
            obj_in_data={
                "username": self._free_username(db, obj_in.name, obj_in.last_name),
                "password": hash_password(INITIAL_PASSWORD),
                "id_person": person.id_person,
                "active": True,
            },
        )
        user_role_repository.add(
            db, obj_in_data={"id_user": user.id_user, "id_role": id_role}
        )
        db.commit()
        return self._driver_row(db, user.id_user)

    def update(
        self, db: Session, *, id_user: int, obj_in: DriverUpdate
    ) -> DriverAdminRow:
        """PATCH parcial de los datos de la persona. `active` desactiva o reactiva
        al domiciliario (usuario y persona): sus asignaciones dejan de ofrecerse al
        asignar pedidos; sus pedidos y cierres se conservan."""
        seller_role = self._seller_role(db, id_user)
        user: User = seller_role.user
        sent = obj_in.model_fields_set
        _ensure_not_null(obj_in, _REQUIRED_DRIVER)

        if "active" in sent and obj_in.active is False and user.active:
            if driver_repository.has_other_roles(db, id_user):
                raise BusinessValidationError(
                    "Este usuario también tiene otro rol (p. ej. ADMINISTRADOR); "
                    "desactivarlo le quitaría el acceso al sistema.",
                    field="active",
                    code="DRIVER_PROTECTED",
                )
            if driver_repository.owns_default_seller(db, seller_role.id_user_role):
                raise _default_seller_error("active")

        person = user.person
        for field in _PERSON_FIELDS:
            if field in sent:
                setattr(person, field, getattr(obj_in, field))
        if "active" in sent:
            user.active = person.active = bool(obj_in.active)
        db.commit()
        return self._driver_row(db, id_user)

    # ------------------------------------------------------------------
    # Asignaciones
    # ------------------------------------------------------------------
    def list_assignments(
        self, db: Session, *, id_user: int
    ) -> list[DriverAssignmentRow]:
        seller_role = self._seller_role(db, id_user)
        rows = driver_repository.get_assignments(db, seller_role.id_user_role)
        return [
            DriverAssignmentRow.model_validate(row, from_attributes=True)
            for row in rows
        ]

    def create_assignment(
        self, db: Session, *, id_user: int, obj_in: DriverAssignmentCreate
    ) -> DriverAssignmentRow:
        seller_role = self._seller_role(db, id_user)
        self._ensure_vehicle(db, obj_in.id_vehicle)
        self._ensure_code_free(db, obj_in.code)
        self._ensure_pair_free(db, seller_role.id_user_role, obj_in.id_vehicle)
        assignment = user_vehicle_repository.add(
            db,
            obj_in_data={
                "code": obj_in.code,
                "id_user_role": seller_role.id_user_role,
                "id_vehicle": obj_in.id_vehicle,
                "active": True,
            },
        )
        db.commit()
        return self._assignment_row(db, assignment.id_user_vehicle)

    def update_assignment(
        self,
        db: Session,
        *,
        id_user: int,
        id_user_vehicle: int,
        obj_in: DriverAssignmentUpdate,
    ) -> DriverAssignmentRow:
        """PATCH parcial: código, vehículo y estado. Con pedidos o cierres solo
        cambia el estado (activar / desactivar)."""
        assignment = self._assignment(db, id_user, id_user_vehicle)
        sent = obj_in.model_fields_set
        _ensure_not_null(obj_in, _REQUIRED_ASSIGNMENT)

        current_code = assignment.code.strip()
        code_changes = "code" in sent and obj_in.code != current_code
        vehicle_changes = (
            "id_vehicle" in sent and obj_in.id_vehicle != assignment.id_vehicle
        )
        if current_code == settings.DEFAULT_SELLER_CODE and (
            code_changes or vehicle_changes or obj_in.active is False
        ):
            raise _default_seller_error("code" if code_changes else "active")
        if (code_changes or vehicle_changes) and driver_repository.is_in_use(
            db, id_user_vehicle
        ):
            raise BusinessValidationError(
                "Esta asignación ya tiene pedidos o cierres: su código y su "
                "vehículo no se cambian (el cierre y Siigo los usan). Desactívala y "
                "crea una nueva.",
                field="code" if code_changes else "id_vehicle",
                code="ASSIGNMENT_IN_USE",
            )
        if code_changes:
            self._ensure_code_free(db, obj_in.code, exclude=assignment)  # type: ignore[arg-type]
        if vehicle_changes:
            self._ensure_vehicle(db, obj_in.id_vehicle)  # type: ignore[arg-type]
            self._ensure_pair_free(
                db,
                assignment.id_user_role,
                obj_in.id_vehicle,  # type: ignore[arg-type]
                exclude=assignment,
            )

        if code_changes:
            assignment.code = obj_in.code  # type: ignore[assignment]
        if vehicle_changes:
            assignment.id_vehicle = obj_in.id_vehicle  # type: ignore[assignment]
        if "active" in sent:
            assignment.active = bool(obj_in.active)
        db.commit()
        return self._assignment_row(db, id_user_vehicle)

    def delete_assignment(
        self, db: Session, *, id_user: int, id_user_vehicle: int
    ) -> None:
        """Borra una asignación que nunca se usó (p. ej. creada por error)."""
        assignment = self._assignment(db, id_user, id_user_vehicle)
        if assignment.code.strip() == settings.DEFAULT_SELLER_CODE:
            raise _default_seller_error("code")
        if driver_repository.is_in_use(db, id_user_vehicle):
            raise BusinessValidationError(
                "Esta asignación ya tiene pedidos o cierres y no se puede borrar. "
                "Desactívala para que no se ofrezca al asignar pedidos.",
                field="id_user_vehicle",
                code="ASSIGNMENT_IN_USE",
            )
        user_vehicle_repository.delete(db, db_obj=assignment)
        db.commit()

    def next_code(self, db: Session) -> NextSellerCode:
        """Primer código libre de 01 a 99 (sugerencia para una asignación nueva)."""
        used = driver_repository.used_codes(db)
        codes = (f"{number:02d}" for number in range(1, 100))
        return NextSellerCode(code=next((c for c in codes if c not in used), None))

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _seller_role(db: Session, id_user: int) -> UserRole:
        seller_role = driver_repository.get_seller_role(db, id_user)
        if seller_role is None:
            raise EntityNotFoundError("Domiciliario", id_user)
        return seller_role

    def _assignment(
        self, db: Session, id_user: int, id_user_vehicle: int
    ) -> UserVehicle:
        seller_role = self._seller_role(db, id_user)
        assignment = user_vehicle_repository.get(db, id_user_vehicle)
        if assignment is None or assignment.id_user_role != seller_role.id_user_role:
            raise EntityNotFoundError("Asignación", id_user_vehicle)
        return assignment

    @staticmethod
    def _free_username(db: Session, name: str, last_name: str) -> str:
        """nombre.apellido; si existe, nombre.apellido2, nombre.apellido3…"""
        base = username_base(name, last_name)
        taken = driver_repository.usernames_like(db, base)
        if base not in taken:
            return base
        suffix = 2
        while f"{base}{suffix}" in taken:
            suffix += 1
        return f"{base}{suffix}"

    @staticmethod
    def _ensure_vehicle(db: Session, id_vehicle: int) -> None:
        ensure_reference(
            db, vehicle_repository, id_vehicle, field="id_vehicle", label="Vehículo"
        )

    @staticmethod
    def _ensure_code_free(
        db: Session, code: str, *, exclude: UserVehicle | None = None
    ) -> None:
        if user_vehicle_repository.exists(db, exclude=exclude, code=code):
            raise ConflictError(
                f"El código {code} ya es de otra asignación domiciliario-vehículo.",
                field="code",
                code="SELLER_CODE_TAKEN",
            )

    @staticmethod
    def _ensure_pair_free(
        db: Session,
        id_user_role: int,
        id_vehicle: int,
        *,
        exclude: UserVehicle | None = None,
    ) -> None:
        if user_vehicle_repository.exists(
            db, exclude=exclude, id_user_role=id_user_role, id_vehicle=id_vehicle
        ):
            raise ConflictError(
                "El domiciliario ya tiene una asignación con ese vehículo. Si está "
                "inactiva, reactívala en lugar de crear otra.",
                field="id_vehicle",
                code="DUPLICATE_ASSIGNMENT",
            )

    @staticmethod
    def _driver_row(db: Session, id_user: int) -> DriverAdminRow:
        row = driver_repository.get_admin_row(db, id_user)
        if row is None:
            raise EntityNotFoundError("Domiciliario", id_user)
        return DriverAdminRow.model_validate(row, from_attributes=True)

    @staticmethod
    def _assignment_row(db: Session, id_user_vehicle: int) -> DriverAssignmentRow:
        row = driver_repository.get_assignment_row(db, id_user_vehicle)
        if row is None:
            raise EntityNotFoundError("Asignación", id_user_vehicle)
        return DriverAssignmentRow.model_validate(row, from_attributes=True)


def _ensure_not_null(obj_in, required: dict[str, str]) -> None:
    """Un PATCH no puede enviar null en columnas NOT NULL."""
    for field, label in required.items():
        if field in obj_in.model_fields_set and getattr(obj_in, field) is None:
            raise BusinessValidationError(
                f"{label} no puede quedar vacío.", field=field, code="REQUIRED_FIELD"
            )


def _default_seller_error(field: str) -> BusinessValidationError:
    return BusinessValidationError(
        "Es el vendedor por defecto del cierre (código "
        f"{settings.DEFAULT_SELLER_CODE}): recibe los pedidos sin conductor, así que "
        "no se desactiva, cambia ni borra.",
        field=field,
        code="DEFAULT_SELLER_PROTECTED",
    )


driver_service = DriverService()
