from pydantic import BaseModel, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import LowerText, UpperText


# Schema Base
class PersonBase(BaseModel):
    name: UpperText = Field(..., max_length=100)
    last_name: UpperText = Field(..., max_length=100)
    phone: str | None = Field(None, pattern=r"^[0-9]{10}$", description="10 dígitos")
    email: LowerText | None = Field(
        None, max_length=100, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    active: bool = True


class PersonCreate(PersonBase):
    pass


@partial_model
class PersonUpdate(PersonBase):
    pass


class PersonResponse(PersonBase):
    id_person: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
