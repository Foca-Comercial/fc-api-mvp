from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import require_roles


class SecuredRouter(APIRouter):
    """
    APIRouter donde cada endpoint exige el rol ADMINISTRADOR por defecto
    (ADMINISTRADOR siempre pasa, vía el bypass de `require_roles`).

    Para permitir otros roles en un endpoint puntual, pasa `roles=[...]`
    al decorador, en vez de agregar `dependencies=[Depends(require_roles(...))]`
    a mano:

        @router.post("/", roles=["SUBADMINISTRADOR"])
        def create_role(...): ...
    """

    def _inject_role_dependency(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        roles = kwargs.pop("roles", None)
        existing = kwargs.get("dependencies") or []
        kwargs["dependencies"] = [*existing, Depends(require_roles(*(roles or ())))]
        return kwargs

    def get(self, path: str, **kwargs: Any) -> Callable:
        return super().get(path, **self._inject_role_dependency(kwargs))

    def post(self, path: str, **kwargs: Any) -> Callable:
        return super().post(path, **self._inject_role_dependency(kwargs))

    def put(self, path: str, **kwargs: Any) -> Callable:
        return super().put(path, **self._inject_role_dependency(kwargs))

    def patch(self, path: str, **kwargs: Any) -> Callable:
        return super().patch(path, **self._inject_role_dependency(kwargs))

    def delete(self, path: str, **kwargs: Any) -> Callable:
        return super().delete(path, **self._inject_role_dependency(kwargs))
