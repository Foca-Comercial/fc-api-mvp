from pydantic import BaseModel, EmailStr, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schema Base
class PersonBase(BaseModel):
    name: UpperText = Field(..., max_length=100)
    last_name: UpperText = Field(..., max_length=100)
    phone: str | None = Field(None, max_length=10)
    email: EmailStr | None = Field(None, max_length=50)
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
