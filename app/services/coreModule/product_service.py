from sqlalchemy.orm import Session

from app.models.coreModule.product import Product
from app.repositories.coreModule.product_repository import product_repository
from app.schemas.common.page_schema import Page, PageParams
from app.schemas.coreModule.product_schema import (
    ProductAdminFilters,
    ProductAdminRow,
    ProductCatalogItem,
    ProductCreate,
    ProductUpdate,
)
from app.services.base_service import BaseService, UniqueRule
from app.utils.exceptions.business_exceptions import (
    BusinessValidationError,
    EntityNotFoundError,
)

# Campos del producto que no pueden quedar en null al editar (columnas NOT NULL)
_REQUIRED_ON_UPDATE = {
    "code": "código",
    "name": "nombre",
    "base_price": "precio base",
    "active": "estado",
}


class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    unique_rules = (UniqueRule("code", "Código de producto"),)

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=product_repository, entity_name="Producto")

    # Obtener listado de productos con sus precios (id_client para precios especiales)
    def get_catalog(
        self, db: Session, *, id_client: int | None = None
    ) -> list[ProductCatalogItem]:
        rows = self.repository.get_catalog(db, id_client=id_client)
        return [
            ProductCatalogItem(
                id_product=p.id_product,
                code=p.code,
                name=p.name,
                base_price=p.base_price,
                agreed_price=agreed_price,
                effective_price=agreed_price
                if agreed_price is not None
                else p.base_price,
            )
            for p, agreed_price in rows
        ]

    # ------------------------------------------------------------------
    # Panel de administración
    # ------------------------------------------------------------------
    def get_admin_page(
        self, db: Session, *, filters: ProductAdminFilters, params: PageParams
    ) -> Page[ProductAdminRow]:
        rows, total = product_repository.get_admin_page(db, filters, params)
        items = [
            ProductAdminRow.model_validate(row, from_attributes=True) for row in rows
        ]
        return Page[ProductAdminRow].build(items, total=total, params=params)

    def create_admin(self, db: Session, *, obj_in: ProductCreate) -> ProductAdminRow:
        self._validate_before_create(db, obj_in)  # código único
        product = product_repository.add(db, obj_in_data=obj_in.model_dump())
        db.commit()
        return self._admin_row(db, product.id_product)

    def update_admin(
        self, db: Session, *, id_product: int, obj_in: ProductUpdate
    ) -> ProductAdminRow:
        """PATCH parcial. `active=False` desactiva el producto (deja de ofrecerse
        en el catálogo y en las rutas; los pedidos ya tomados lo conservan) y
        `active=True` lo reactiva. Un cambio de precio base aplica a los pedidos
        que se tomen después (cada pedido guarda su precio)."""
        product = self.get(db, id_product)
        sent = obj_in.model_fields_set
        for field, label in _REQUIRED_ON_UPDATE.items():
            if field in sent and getattr(obj_in, field) is None:
                raise BusinessValidationError(
                    f"El {label} del producto no puede quedar vacío.",
                    field=field,
                    code="REQUIRED_FIELD",
                )
        # El cierre, la exportación a Siigo y el archivado leen el código actual del
        # producto: cambiarlo reescribiría cómo se ven los pedidos ya tomados.
        if (
            obj_in.code is not None
            and obj_in.code != product.code
            and product_repository.has_orders(db, id_product)
        ):
            raise BusinessValidationError(
                "El código no se puede cambiar: el producto ya tiene pedidos. Si "
                "necesitas otro código, crea un producto nuevo y desactiva este.",
                field="code",
                code="PRODUCT_CODE_IN_USE",
            )
        self._validate_before_update(db, obj_in, product)  # código único
        product_repository.update(db, db_obj=product, obj_in=obj_in)
        return self._admin_row(db, id_product)

    @staticmethod
    def _admin_row(db: Session, id_product: int) -> ProductAdminRow:
        row = product_repository.get_admin_row(db, id_product)
        if row is None:
            raise EntityNotFoundError("Producto", id_product)
        return ProductAdminRow.model_validate(row, from_attributes=True)


# Instancia única para inyectar en el router
product_service = ProductService()
