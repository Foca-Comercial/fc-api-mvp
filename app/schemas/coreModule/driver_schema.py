"""Panel de administración: domiciliarios y sus asignaciones con vehículos.

Un domiciliario no es una tabla: es la cadena Person + User + UserRole (rol
VENDEDOR). Cada asignación (`user_vehicle`) es la pareja domiciliario + vehículo con
su propio código de 2 dígitos, que es el código de vendedor en Siigo: un
domiciliario tiene un código por cada vehículo que maneja.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText

PHONE_PATTERN = r"^\d{10}$"
SELLER_CODE_PATTERN = r"^\d{2}$"


# -----------------------------------------------------
# Domiciliario (datos de la persona)
# -----------------------------------------------------
class DriverCreate(BaseModel):
    """El usuario (nombre.apellido) y la contraseña inicial los pone el servicio."""

    name: UpperText = Field(..., max_length=100)
    last_name: UpperText = Field(..., max_length=100)
    phone: str | None = Field(None, pattern=PHONE_PATTERN, description="10 dígitos")
    email: EmailStr | None = Field(None, max_length=50)


# PATCH parcial. `active` desactiva o reactiva al domiciliario (su usuario y persona).
@partial_model
class DriverUpdate(DriverCreate):
    active: bool | None = None


@dataclass(frozen=True)
class DriverAdminFilters:
    search: str | None = None  # nombre o apellido (contiene) o código (empieza por)
    active: bool | None = None  # None = activos e inactivos


class DriverAdminRow(BaseModel):
    id_user: int
    id_person: int
    name: str
    last_name: str
    phone: str | None
    email: str | None
    username: str
    active: bool
    codes: list[str] = Field(
        ..., description="Códigos de sus asignaciones activas, en orden"
    )
    assignments_count: int = Field(..., description="Asignaciones activas")
    protected: bool = Field(
        ...,
        description="No se puede desactivar: tiene otro rol (p. ej. ADMINISTRADOR) o "
        "es el vendedor por defecto del cierre",
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("codes", mode="before")
    @classmethod
    def _no_codes(cls, value: list[str] | None) -> list[str]:
        # array_agg: NULL sin asignaciones y sin orden garantizado; CHAR(2) con espacios
        return sorted(code.strip() for code in value or [])


# -----------------------------------------------------
# Asignaciones (domiciliario + vehículo + código)
# -----------------------------------------------------
class DriverAssignmentCreate(BaseModel):
    id_vehicle: int = Field(..., gt=0)
    code: str = Field(
        ...,
        pattern=SELLER_CODE_PATTERN,
        description="Código de vendedor: 2 dígitos, único (en Siigo es un número)",
    )


# PATCH parcial. Una asignación con pedidos o cierres solo puede cambiar `active`.
@partial_model
class DriverAssignmentUpdate(DriverAssignmentCreate):
    active: bool | None = None


class DriverAssignmentRow(BaseModel):
    id_user_vehicle: int
    code: str
    active: bool
    id_vehicle: int
    vehicle_name: str
    vehicle_active: bool
    in_use: bool = Field(
        ...,
        description="Tiene pedidos o cierres: código y vehículo ya no se pueden "
        "cambiar, ni se puede borrar (sí desactivar)",
    )
    is_default: bool = Field(
        ..., description="Vendedor por defecto del cierre (DEFAULT_SELLER_CODE)"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("code", mode="before")
    @classmethod
    def _strip_code(cls, value: str) -> str:
        return value.strip()


class NextSellerCode(BaseModel):
    code: str | None = Field(
        ..., description="Primer código libre de 01 a 99 (null si no quedan)"
    )
