from app.models.securityModule.person import Person
from app.repositories.securityModule.person_repository import person_repository
from app.schemas.securityModule.person_schema import PersonCreate, PersonUpdate
from app.services.base_service import BaseService


class PersonService(BaseService[Person, PersonCreate, PersonUpdate]):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=person_repository, entity_name="Persona")


# Instancia única para inyectar en el router
person_service = PersonService()
