import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.utils.exceptions.business_exceptions import (
    BusinessError,
    BusinessRuleViolationError,
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
    ExternalServiceError,
    ForbiddenError,
    UnauthorizedError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_EXCEPTION: dict[type[BusinessError], HTTPStatus] = {
    EntityNotFoundError: HTTPStatus.NOT_FOUND,
    BusinessValidationError: HTTPStatus.UNPROCESSABLE_ENTITY,
    ConflictError: HTTPStatus.CONFLICT,
    BusinessRuleViolationError: HTTPStatus.UNPROCESSABLE_ENTITY,
    UnauthorizedError: HTTPStatus.UNAUTHORIZED,
    ForbiddenError: HTTPStatus.FORBIDDEN,
    ExternalServiceError: HTTPStatus.BAD_GATEWAY,
}

# Códigos de error de BD: SQLSTATE de PostgreSQL (str) y errno de MySQL (int)
_UNIQUE_VIOLATION = {"23505", 1062}
_FOREIGN_KEY_VIOLATION = {"23503", 1451, 1452}


def _status_for(exc: BusinessError) -> HTTPStatus:
    # Recorre la jerarquía: una subclase futura hereda el estado de su padre
    for cls in type(exc).__mro__:
        if cls in _STATUS_BY_EXCEPTION:
            return _STATUS_BY_EXCEPTION[cls]  # type: ignore[index]
    return HTTPStatus.BAD_REQUEST


def _db_error_code(exc: IntegrityError) -> str | int | None:
    orig = exc.orig
    code = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if code:
        return code
    args = getattr(orig, "args", ())
    return args[0] if args else None


def _error_body(
    detail: str, code: str, field: str | None = None
) -> dict[str, str | None]:
    return {"detail": detail, "code": code, "field": field}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_error_handler(
        request: Request, exc: BusinessError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=_status_for(exc),
            content=_error_body(exc.message, exc.code, exc.field),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        # El detalle técnico va al log, nunca al cliente
        logger.warning("IntegrityError: %s", exc.orig)
        db_code = _db_error_code(exc)

        if db_code in _UNIQUE_VIOLATION:
            return JSONResponse(
                status_code=HTTPStatus.CONFLICT,
                content=_error_body(
                    "Ya existe un registro con esos datos.", "DUPLICATE_ENTRY"
                ),
            )
        if db_code in _FOREIGN_KEY_VIOLATION:
            return JSONResponse(
                status_code=HTTPStatus.CONFLICT,
                content=_error_body(
                    "La operación no es posible por su relación con otros registros.",
                    "RELATED_RECORD",
                ),
            )
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=_error_body(
                "La operación viola una restricción de datos.", "INTEGRITY_ERROR"
            ),
        )
