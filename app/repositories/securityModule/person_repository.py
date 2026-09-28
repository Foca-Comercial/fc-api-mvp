from app.models.securityModule.person import Person
from app.repositories.base_repository import BaseRepository
from app.schemas.securityModule.person_schema import PersonCreate, PersonUpdate


class RepositoryPerson(BaseRepository[Person, PersonCreate, PersonUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
person_repository = RepositoryPerson(Person)
