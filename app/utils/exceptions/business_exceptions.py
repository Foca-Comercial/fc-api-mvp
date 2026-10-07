from typing import Any, ClassVar


class BusinessError(Exception):
    """Excepción base de la capa de negocio. No conoce nada de HTTP."""

    default_code: ClassVar[str] = "BUSINESS_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.field = field


class EntityNotFoundError(BusinessError):
    """No se encontró la entidad solicitada."""

    default_code = "ENTITY_NOT_FOUND"

    def __init__(self, entity_type: str, entity_id: Any) -> None:
        super().__init__(
            f"La entidad '{entity_type}' con ID '{entity_id}' no fue encontrada."
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class BusinessValidationError(BusinessError):
    """Los datos no cumplen una regla de validación. Usa `field` para indicar cuál."""

    default_code = "VALIDATION_ERROR"


class ConflictError(BusinessError):
    """La operación choca con el estado actual (p. ej. un valor ya registrado)."""

    default_code = "CONFLICT"


class BusinessRuleViolationError(BusinessError):
    """Se intentó una operación que viola una regla de negocio."""

    default_code = "BUSINESS_RULE_VIOLATION"

    def __init__(self, message: str, *, rule_code: str | None = None) -> None:
        super().__init__(message, code=rule_code)


class UnauthorizedError(BusinessError):
    """No autenticado: credenciales ausentes o inválidas."""

    default_code = "UNAUTHORIZED"

    def __init__(self, message: str = "Credenciales inválidas o ausentes.") -> None:
        super().__init__(message)


class ForbiddenError(BusinessError):
    """Autenticado, pero sin permisos para el recurso."""

    default_code = "FORBIDDEN"

    def __init__(self, message: str = "No tienes permisos para este recurso.") -> None:
        super().__init__(message)


class ExternalServiceError(BusinessError):
    """Falló un servicio externo (p. ej. la exportación a Siigo)."""

    default_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, service_name: str, message: str) -> None:
        super().__init__(f"Error en el servicio externo '{service_name}': {message}")
        self.service_name = service_name
