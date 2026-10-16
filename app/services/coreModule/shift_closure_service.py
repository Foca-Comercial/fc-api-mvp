"""Cierre del día: consolida por vendedor los pedidos despachados y entregados.

Reglas:
- Un pedido pertenece al día (Bogotá) en que se creó.
- Se facturan solo DISPATCHED y DELIVERED; PENDING y CANCELLED solo cuentan
  en las cards.
- Los pedidos sin conductor se suman al vendedor por defecto
  (settings.DEFAULT_SELLER_CODE). La asignación ocurre solo aquí: el pedido
  no se modifica.
- Siigo recibe el código del vendedor como número ("01" -> 1).
- Exportar (o reexportar) guarda un shift_closure por vendedor y día con
  exported_siigo=True; reexportar actualiza esas filas.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import today_bogota
from app.models.coreModule.shift_closure import ShiftClosure
from app.repositories.coreModule.order_repository import order_repository
from app.repositories.coreModule.shift_closure_repository import (
    shift_closure_repository,
)
from app.repositories.coreModule.user_vehicle_repository import (
    user_vehicle_repository,
)
from app.schemas.coreModule.shift_closure_schema import (
    ClosureCards,
    ClosureProduct,
    ClosureSellerRow,
    ShiftClosureCreate,
    ShiftClosureSummary,
    ShiftClosureUpdate,
)
from app.services.base_service import BaseService
from app.services.coreModule.closure_export import (
    build_closure_workbook,
    filename_for,
)
from app.utils.enums.order_state import OrderState
from app.utils.exceptions.business_exceptions import (
    BusinessRuleViolationError,
    BusinessValidationError,
)


def siigo_seller_code(code: str) -> int:
    """Código del vendedor como lo espera Siigo: número sin ceros a la izquierda."""
    code = code.strip()
    if not code.isdigit():
        raise BusinessRuleViolationError(
            f"El vendedor con código '{code}' no tiene un código numérico y Siigo "
            "lo requiere como número. Corrige el código en /user_vehicles.",
            rule_code="INVALID_SELLER_CODE",
        )
    return int(code)


@dataclass
class ClosureLine:
    """Renglón de factura: un producto a un precio, con sus unidades del día."""

    id_product: int
    product_code: str
    product_name: str
    unit_price: Decimal
    quantity: int = 0
    subtotal: Decimal = Decimal(0)


@dataclass
class SellerClosure:
    """Factura global de un vendedor en un día."""

    id_user_vehicle: int
    code: str
    seller_code: int
    seller_name: str
    orders_count: int = 0
    unassigned_orders: int = 0
    _lines: dict[tuple[int, Decimal], ClosureLine] = field(default_factory=dict)

    def add_line(self, row) -> None:
        # Fusiona por (producto, precio): los pedidos sin conductor y los propios
        # del vendedor por defecto pueden traer el mismo renglón.
        key = (row.id_product, row.unit_price)
        line = self._lines.get(key)
        if line is None:
            line = self._lines[key] = ClosureLine(
                id_product=row.id_product,
                product_code=row.product_code,
                product_name=row.product_name,
                unit_price=row.unit_price,
            )
        line.quantity += int(row.quantity)
        line.subtotal += Decimal(row.subtotal)

    @property
    def lines(self) -> list[ClosureLine]:
        return sorted(
            self._lines.values(), key=lambda li: (li.product_code, li.unit_price)
        )

    @property
    def total_quantity(self) -> int:
        return sum(li.quantity for li in self._lines.values())

    @property
    def total_sales(self) -> Decimal:
        return sum((li.subtotal for li in self._lines.values()), Decimal(0))

    def products(self) -> list[ClosureProduct]:
        """Unidades por producto, sumando los distintos precios."""
        by_product: dict[str, ClosureProduct] = {}
        for li in self.lines:
            product = by_product.get(li.product_code)
            if product is None:
                product = by_product[li.product_code] = ClosureProduct(
                    product_code=li.product_code,
                    product_name=li.product_name,
                    quantity=0,
                )
            product.quantity += li.quantity
        return list(by_product.values())


class ShiftClosureService(
    BaseService[ShiftClosure, ShiftClosureCreate, ShiftClosureUpdate]
):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=shift_closure_repository, entity_name="CierreTurno")

    # ------------------------------------------------------------------
    # Resumen del día (vista Cierre)
    # ------------------------------------------------------------------
    def get_summary(self, db: Session, target_date: date) -> ShiftClosureSummary:
        self._ensure_closable_date(target_date)
        counts = order_repository.count_by_state_on_day(db, target_date)
        sellers = self.consolidate(db, target_date)
        closures = shift_closure_repository.get_by_date(db, target_date)

        rows = [
            self._to_row(seller, closures.get(seller.id_user_vehicle))
            for seller in sellers
        ]
        # Un cierre exportado de un vendedor que ya no tiene pedidos facturables
        # (p. ej. se le reasignaron) también deja la exportación desactualizada.
        current_ids = {seller.id_user_vehicle for seller in sellers}
        stale = any(
            closure.exported_siigo
            for id_uv, closure in closures.items()
            if id_uv not in current_ids
        )
        exported = (
            bool(rows)
            and not stale
            and all(r.exported_at is not None and not r.export_outdated for r in rows)
        )

        cards = ClosureCards(
            total_orders=sum(counts.values()),
            pending=counts.get(OrderState.PENDING, 0),
            dispatched=counts.get(OrderState.DISPATCHED, 0),
            delivered=counts.get(OrderState.DELIVERED, 0),
            cancelled=counts.get(OrderState.CANCELLED, 0),
            sellers_count=len(rows),
            total_income=sum((r.total_sales for r in rows), Decimal(0)),
        )
        return ShiftClosureSummary(
            closure_date=target_date, exported=exported, cards=cards, sellers=rows
        )

    # ------------------------------------------------------------------
    # Exportación a Siigo (.xlsx)
    # ------------------------------------------------------------------
    def export_day(self, db: Session, closure_date: date) -> tuple[str, bytes]:
        """Genera el Excel del día y registra los cierres como exportados.

        Devuelve (nombre del archivo, contenido). Se puede repetir: cada
        exportación refleja los pedidos actuales y actualiza los cierres.
        """
        self._ensure_closable_date(closure_date)
        sellers = self.consolidate(db, closure_date)
        if not sellers:
            raise BusinessRuleViolationError(
                f"El {closure_date.strftime('%d/%m/%Y')} no tiene pedidos despachados "
                "ni entregados para exportar.",
                rule_code="NO_BILLABLE_ORDERS",
            )

        # El archivo se arma antes de escribir en la BD: si falla, no queda
        # ningún cierre marcado como exportado.
        content = build_closure_workbook(closure_date, sellers)
        shift_closure_repository.save_exported(
            db,
            closure_date,
            [(s.id_user_vehicle, s.orders_count, s.total_sales) for s in sellers],
        )
        db.commit()
        return filename_for(closure_date), content

    # ------------------------------------------------------------------
    # Consolidación (la usan el resumen y la exportación)
    # ------------------------------------------------------------------
    def consolidate(self, db: Session, day: date) -> list[SellerClosure]:
        """Facturas globales del día, una por vendedor, ordenadas por código."""
        counts = order_repository.count_billable_by_seller(db, day)
        if not counts:
            return []

        default_id = self._default_seller_id(db) if None in counts else None

        def owner(id_user_vehicle: int | None) -> int:
            if id_user_vehicle is None:
                assert default_id is not None  # se resolvió arriba
                return default_id
            return id_user_vehicle

        ids = {owner(id_uv) for id_uv in counts}
        info = user_vehicle_repository.get_sellers(db, ids)
        sellers: dict[int, SellerClosure] = {}
        for id_uv in ids:
            code, name = info[id_uv]
            sellers[id_uv] = SellerClosure(
                id_user_vehicle=id_uv,
                code=code.strip(),
                seller_code=siigo_seller_code(code),
                seller_name=name,
            )

        for id_uv, orders in counts.items():
            seller = sellers[owner(id_uv)]
            seller.orders_count += orders
            if id_uv is None:
                seller.unassigned_orders = orders

        for row in order_repository.get_billable_lines(db, day):
            sellers[owner(row.id_user_vehicle)].add_line(row)  # type: ignore

        return sorted(sellers.values(), key=lambda s: s.seller_code)

    @staticmethod
    def _default_seller_id(db: Session) -> int:
        code = settings.DEFAULT_SELLER_CODE
        id_user_vehicle = user_vehicle_repository.get_id_by_code(db, code)
        if id_user_vehicle is None:
            raise BusinessRuleViolationError(
                f"Hay pedidos despachados sin conductor y no existe el vendedor por "
                f"defecto con código '{code}'. Créalo en /user_vehicles (o ajusta "
                "DEFAULT_SELLER_CODE) para poder cerrar el día.",
                rule_code="DEFAULT_SELLER_MISSING",
            )
        return id_user_vehicle

    @staticmethod
    def _ensure_closable_date(day: date) -> None:
        if day > today_bogota():
            raise BusinessValidationError(
                "No se puede cerrar un día que aún no ha llegado.",
                field="target_date",
                code="INVALID_CLOSURE_DATE",
            )

    @staticmethod
    def _to_row(
        seller: SellerClosure, closure: ShiftClosure | None
    ) -> ClosureSellerRow:
        exported_at = None
        outdated = False
        if closure is not None and closure.exported_siigo:
            exported_at = closure.exported_at
            outdated = (
                closure.total_orders != seller.orders_count
                or closure.total_sales != seller.total_sales
            )
        return ClosureSellerRow(
            id_user_vehicle=seller.id_user_vehicle,
            seller_code=seller.seller_code,
            seller_name=seller.seller_name,
            products=seller.products(),
            total_quantity=seller.total_quantity,
            orders_count=seller.orders_count,
            unassigned_orders=seller.unassigned_orders,
            total_sales=seller.total_sales,
            exported_at=exported_at,
            export_outdated=outdated,
        )


# Instancia única para inyectar en el router
shift_closure_service = ShiftClosureService()
