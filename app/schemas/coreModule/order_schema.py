from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.coreModule.client_schema import NewClientInput
from app.schemas.coreModule.order_detail_schema import OrderDetailResponse
from app.utils.enums.cancel_reason import CancelReason
from app.utils.enums.invoice_type import InvoiceType
from app.utils.enums.order_state import OrderState
from app.utils.enums.payment_method import PaymentMethod
from app.utils.schema_types import TrimmedText

OBSERVATIONS_MAX = 500


# Schema Base
class OrderBase(BaseModel):
    purchase_order: str = Field(
        ..., max_length=3, description="Número de orden de compra"
    )
    estimated_delivery: time | None = Field(
        None, description="Hora estimada de entrega"
    )
    order_total: Decimal | None = Field(None, ge=0, description="Total del pedido")
    id_client: int = Field(..., description="Cliente que realiza el pedido")
    id_user_vehicle: int | None = Field(None, description="Conductor/vehículo asignado")


class OrderCreate(OrderBase):
    pass


# -----------------------------------------------------
# Registro de Pedidos: Ítems y Cargas Base
# -----------------------------------------------------
class OrderItemInput(BaseModel):
    id_product: int = Field(..., description="Producto vendido")
    cant: int = Field(..., gt=0, description="Cantidad vendida")
    unit_price: Decimal = Field(..., ge=0, description="Precio Especial")


class OrderCreateBase(BaseModel):
    # Sin purchase_order: el servidor asigna el consecutivo del día de entrega.
    estimated_delivery: time | None = None
    delivery_date: date | None = Field(
        None,
        description="Día de entrega (Bogotá). Si no se envía, es hoy. "
        "Para programar un pedido: una fecha futura (máx. 60 días)",
    )
    id_user_vehicle: int | None = Field(None, description="Opcional")
    payment_method: PaymentMethod = Field(
        PaymentMethod.CASH, description="Efectivo, transferencia o crédito"
    )
    invoice_type: InvoiceType | None = Field(
        None,
        description="Sin valor: la del cliente (ELECTRONIC si requiere factura "
        "electrónica, si no POS). Un cliente temporal solo admite POS",
    )
    observations: TrimmedText | None = Field(
        None, max_length=OBSERVATIONS_MAX, description="Observación general"
    )
    items: list[OrderItemInput] = Field(..., min_length=1)


# -----------------------------------------------------
# Registro de Pedidos: Variantes por Tipo de Cliente
# -----------------------------------------------------
class OrderCreateNewClient(OrderCreateBase):
    client: NewClientInput


class OrderCreateExistingClient(OrderCreateBase):
    id_client: int


# PATCH acotado a los campos operativos del pedido. No hereda de OrderBase a
# propósito (purchase_order, order_total e id_client no se modifican por esta
# vía; los items van por sync_items).
class OrderUpdate(BaseModel):
    """PATCH parcial: solo se modifica lo enviado."""

    id_user_vehicle: int | None = Field(
        None, description="Vehículo a asignar (null para desasignar)"
    )
    estimated_delivery: time | None = Field(
        None,
        description="Hora estimada de entrega (null para quitarla). "
        "Solo editable mientras el pedido está PENDING",
    )
    delivery_date: date | None = Field(
        None,
        description="Nuevo día de entrega (no admite null). Solo editable mientras "
        "el pedido está PENDING; recibe un consecutivo nuevo del día de destino",
    )
    payment_method: PaymentMethod | None = Field(
        None,
        description="No admite null. Editable en PENDING y DISPATCHED (p. ej. el "
        "cliente decide pagar por transferencia al recibir)",
    )
    invoice_type: InvoiceType | None = Field(
        None,
        description="No admite null. Editable en PENDING y DISPATCHED; un cliente "
        "temporal solo admite POS",
    )
    observations: TrimmedText | None = Field(
        None,
        max_length=OBSERVATIONS_MAX,
        description="Observación general (null la borra). Editable en PENDING y "
        "DISPATCHED",
    )


# -----------------------------------------------------
# Actualiacion de Pedido (Quitar, Agregar, Modificar -> Productos)
# -----------------------------------------------------
class OrderItemSync(BaseModel):
    id_order_detail: int | None = Field(None, description="Null para un producto nuevo")
    id_product: int
    cant: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class OrderItemsSyncRequest(BaseModel):
    items: list[OrderItemSync] = Field(..., min_length=1)


# -----------------------------------------------------
# Registro de Pedidos: Respuesta tras registrar un pedido
# -----------------------------------------------------
class OrderResponse(OrderBase):
    id_order: int
    id_user_taker: int
    id_route: int | None = None
    creation_datetime: datetime
    delivery_date: date
    dispatch_time: time | None
    delivery_time: time | None
    state: OrderState
    payment_method: PaymentMethod
    invoice_type: InvoiceType
    observations: str | None = None
    has_receipt: bool = Field(
        ..., description="Lleva comprobante de despacho: solo POS + efectivo"
    )
    items_updated_at: datetime | None = Field(
        None, description="Última edición de los productos (null si nunca)"
    )

    model_config = ConfigDict(from_attributes=True)


class OrderWithDetailsResponse(OrderResponse):
    order_details: list[OrderDetailResponse] = []


# -----------------------------------------------------
# Schema para la Tabla Principal (Dashboard)
# -----------------------------------------------------
class OrderSummaryResponse(BaseModel):
    id_order: int
    purchase_order: str
    creation_time: str
    estimated_delivery: time | None = None
    client_name: str
    zone_name: str
    product_codes: str
    total_quantity: int
    driver_code: str | None
    driver_name: str | None
    state: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Schemas para el Modal de Detalles
# -----------------------------------------------------
class OrderDetailItemModal(BaseModel):
    id_order_detail: int
    id_product: int
    product_code: str
    product_name: str
    product_active: bool = Field(
        True,
        description="Un producto desactivado después de tomar el pedido se conserva "
        "en su renglón, pero no se puede volver a agregar",
    )
    cant: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderFullDetailResponse(BaseModel):
    id_order: int
    purchase_order: str
    creation_datetime: datetime = Field(..., description="Hora de Bogotá")
    creation_date: date = Field(..., description="Día en que se tomó (Bogotá)")
    creation_time: str = Field(..., description="Hora en que se tomó, HH:MM (Bogotá)")
    delivery_date: date
    estimated_delivery: time | None
    dispatch_time: time | None
    delivery_time: time | None
    state: str
    order_total: Decimal

    # Facturación y observación
    payment_method: PaymentMethod
    invoice_type: InvoiceType
    has_receipt: bool
    observations: str | None = None

    # Ruta de la que se generó (null = pedido individual)
    id_route: int | None = None
    route_name: str | None = None

    # Auditoría
    taker_name: str = Field(..., description="Quién registró el pedido")
    items_updater_name: str | None = Field(
        None, description="Quién editó los productos por última vez"
    )
    items_updated_at: datetime | None = Field(
        None, description="Cuándo se editaron los productos por última vez (Bogotá)"
    )

    # Cancelación (solo si state = CANCELLED)
    cancel_reason: CancelReason | None = None
    cancel_note: str | None = None
    cancelled_at: datetime | None = None
    canceller_name: str | None = None

    # Datos del Cliente Expandidos
    id_client: int
    client_name: str
    client_phone: str | None
    client_address: str | None
    neighborhood_name: str
    zone_name: str

    # Datos del Domiciliario (Si aplica)
    id_user_vehicle: int | None
    driver_code: str | None
    driver_name: str | None

    # Lista de Productos
    items: list[OrderDetailItemModal]

    model_config = ConfigDict(from_attributes=True)
