"""Cierre del día por vendedor: resumen y exportación.

Reglas:
- Un pedido pertenece a su día de entrega (delivery_date, Bogotá).
- Se facturan DISPATCHED y DELIVERED; PENDING y CANCELLED solo cuentan en las
  cards (los cancelados después de despacharse, además, en un listado aparte).
- Los pedidos sin conductor se suman al vendedor por defecto
  (settings.DEFAULT_SELLER_CODE). La asignación ocurre solo aquí: el pedido no
  se modifica.
- Cada pedido cae en una categoría (tipo de factura x método de pago). Solo
  POS + efectivo va a la factura global; el resto se factura aparte en Siigo.
  El cálculo vive en closure_consolidation.py (sin BD).
- Siigo recibe el código del vendedor como número ("01" -> 1).
- Exportar (o reexportar) guarda un shift_closure por vendedor y día con la
  huella de sus pedidos; reexportar actualiza esas filas.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import BOGOTA_TZ, today_bogota
from app.models.coreModule.shift_closure import ShiftClosure
from app.repositories.coreModule.order_repository import order_repository
from app.repositories.coreModule.shift_closure_repository import (
    ExportedClosure,
    shift_closure_repository,
)
from app.repositories.coreModule.user_vehicle_repository import (
    user_vehicle_repository,
)
from app.schemas.coreModule.shift_closure_schema import (
    ClosureCards,
    ClosureCategoryTotals,
    ClosureProduct,
    ClosureSellerRow,
    ShiftClosureCreate,
    ShiftClosureSummary,
    ShiftClosureUpdate,
)
from app.services.base_service import BaseService
from app.services.coreModule.closure_consolidation import (
    CATEGORIES,
    CancelledOrder,
    ClosureOrder,
    ClosureOrderLine,
    SellerClosure,
)
from app.services.coreModule.closure_export import (
    build_closure_workbook,
    filename_for,
)
from app.utils.enums.order_state import OrderState
from app.utils.exceptions.business_exceptions import (
    BusinessError,
    BusinessRuleViolationError,
    BusinessValidationError,
)


def siigo_seller_code(code: str) -> int:
    """Código del vendedor como lo espera Siigo: número sin ceros a la izquierda."""
    code = code.strip()
    if not code.isdigit():
        raise BusinessRuleViolationError(
            f"El vendedor con código '{code}' no tiene un código numérico y Siigo "
            "lo requiere como número. Corrige el código en Gestión → "
            "Domiciliarios.",
            rule_code="INVALID_SELLER_CODE",
        )
    return int(code)


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
        cancelled_after_dispatch = order_repository.get_cancelled_after_dispatch(
            db, target_date
        )

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
            cancelled_after_dispatch=len(cancelled_after_dispatch),
            sellers_count=len(rows),
            totals=_category_totals(sellers),
            total_income=sum((s.total_sales for s in sellers), Decimal(0)),
            cash_to_collect=sum((s.cash_to_collect for s in sellers), Decimal(0)),
        )
        return ShiftClosureSummary(
            closure_date=target_date, exported=exported, cards=cards, sellers=rows
        )

    # ------------------------------------------------------------------
    # Exportación (.xlsx)
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
        content = build_closure_workbook(
            closure_date, sellers, self.cancelled_after_dispatch(db, closure_date)
        )
        shift_closure_repository.save_exported(
            db,
            closure_date,
            [
                ExportedClosure(
                    id_user_vehicle=s.id_user_vehicle,
                    total_orders=s.orders_count,
                    total_sales=s.total_sales,
                    signature=s.signature,
                )
                for s in sellers
            ],
        )
        db.commit()
        return filename_for(closure_date), content

    # ------------------------------------------------------------------
    # Días sin cerrar (bloqueo de la purga y vista Archivo mensual)
    # ------------------------------------------------------------------
    def unclosed_days(self, db: Session, month: date) -> list[date]:
        """Días del mes con pedidos facturables cuyo cierre no está exportado o
        cambió después de exportarse. Usa el mismo cálculo (y la misma huella)
        que el resumen del cierre, así que la purga y la vista Cierre nunca
        discrepan sobre si un día está cerrado."""
        exported = shift_closure_repository.get_exported_in_month(db, month)
        unclosed: list[date] = []
        for day in order_repository.get_billable_days(db, month):
            closures = exported.get(day)
            if not closures:
                unclosed.append(day)  # nunca se exportó
                continue
            try:
                sellers = self.consolidate(db, day)
            except BusinessError:
                # P. ej. falta el vendedor por defecto: el día no se puede cerrar
                unclosed.append(day)
                continue
            current = {s.id_user_vehicle: s for s in sellers}
            if set(current) != set(closures) or any(
                _is_outdated(seller, closures[id_uv])
                for id_uv, seller in current.items()
            ):
                unclosed.append(day)
        return unclosed

    # ------------------------------------------------------------------
    # Consolidación (la usan el resumen, la exportación y la purga)
    # ------------------------------------------------------------------
    def consolidate(self, db: Session, day: date) -> list[SellerClosure]:
        """Cierre del día por vendedor, ordenado por código. Carga los pedidos
        facturables con sus renglones en UNA consulta y todo lo demás se calcula
        sobre esos mismos objetos (closure_consolidation.py)."""
        orders: dict[int, ClosureOrder] = {}
        owners: dict[int, int | None] = {}  # id_order -> id_user_vehicle
        for row in order_repository.get_billable_order_lines(db, day):
            order = orders.get(row.id_order)
            if order is None:
                order = orders[row.id_order] = ClosureOrder(
                    id_order=row.id_order,
                    purchase_order=row.purchase_order,
                    state=row.state,
                    payment_method=row.payment_method,
                    invoice_type=row.invoice_type,
                    client_name=row.client_name,
                    unassigned=row.id_user_vehicle is None,
                )
                owners[row.id_order] = row.id_user_vehicle
            order.lines.append(
                ClosureOrderLine(
                    id_product=row.id_product,
                    product_code=row.product_code,
                    product_name=row.product_name,
                    quantity=row.cant,
                    unit_price=row.unit_price,
                    subtotal=row.subtotal,
                )
            )
        if not orders:
            return []

        unassigned = any(owner is None for owner in owners.values())
        default_id = self._default_seller_id(db) if unassigned else None

        def owner_of(id_order: int) -> int:
            owner = owners[id_order]
            if owner is None:
                assert default_id is not None  # se resolvió arriba
                return default_id
            return owner

        ids = {owner_of(id_order) for id_order in orders}
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
        for id_order, order in orders.items():
            sellers[owner_of(id_order)].orders.append(order)

        return sorted(sellers.values(), key=lambda s: s.seller_code)

    @staticmethod
    def cancelled_after_dispatch(db: Session, day: date) -> list[CancelledOrder]:
        """Pedidos del día que se despacharon y luego se cancelaron (no suman)."""
        return [
            CancelledOrder(
                purchase_order=row.purchase_order,
                seller=(
                    f"{int(row.driver_code)} - {row.driver_name}"
                    if row.driver_code and row.driver_code.strip().isdigit()
                    else row.driver_name or "Sin conductor"
                ),
                client_name=row.client_name,
                payment_method=row.payment_method,
                invoice_type=row.invoice_type,
                total=row.order_total or Decimal(0),
                cancel_reason=row.cancel_reason,
                cancel_note=row.cancel_note,
                canceller_name=row.canceller_name,
                cancelled_at=(
                    row.cancelled_at.astimezone(BOGOTA_TZ) if row.cancelled_at else None
                ),
            )
            for row in order_repository.get_cancelled_after_dispatch(db, day)
        ]

    @staticmethod
    def _default_seller_id(db: Session) -> int:
        code = settings.DEFAULT_SELLER_CODE
        id_user_vehicle = user_vehicle_repository.get_id_by_code(db, code)
        if id_user_vehicle is None:
            raise BusinessRuleViolationError(
                f"Hay pedidos despachados sin conductor y no existe el vendedor por "
                f"defecto con código '{code}'. Créalo en Gestión → Domiciliarios "
                "(o ajusta DEFAULT_SELLER_CODE) para poder cerrar el día.",
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
            outdated = _is_outdated(seller, closure)
        return ClosureSellerRow(
            id_user_vehicle=seller.id_user_vehicle,
            seller_code=seller.seller_code,
            seller_name=seller.seller_name,
            products=[
                ClosureProduct(
                    product_code=p.product_code,
                    product_name=p.product_name,
                    quantity=p.quantity,
                )
                for p in seller.consolidated_products()
            ],
            total_quantity=seller.consolidated_quantity,
            consolidated_total=seller.consolidated_total,
            orders_count=seller.orders_count,
            other_orders_count=len(seller.other_orders),
            unassigned_orders=seller.unassigned_orders,
            totals=_category_totals([seller]),
            total_sales=seller.total_sales,
            cash_to_collect=seller.cash_to_collect,
            exported_at=exported_at,
            export_outdated=outdated,
        )


def _is_outdated(seller: SellerClosure, closure: ShiftClosure) -> bool:
    """¿Cambiaron los pedidos del vendedor después de exportar su cierre?"""
    if closure.signature is not None:
        return closure.signature != seller.signature
    # Cierres exportados antes de la huella: se comparan por cantidad y total
    return (
        closure.total_orders != seller.orders_count
        or closure.total_sales != seller.total_sales
    )


def _category_totals(sellers: list[SellerClosure]) -> ClosureCategoryTotals:
    """Totales por categoría de uno o varios vendedores."""
    totals = {c.key: Decimal(0) for c in CATEGORIES}
    for seller in sellers:
        for key, value in seller.totals_by_category.items():
            totals[key] += value
    return ClosureCategoryTotals(**totals)


# Instancia única para inyectar en el router
shift_closure_service = ShiftClosureService()
