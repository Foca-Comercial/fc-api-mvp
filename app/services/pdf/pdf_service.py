import io
import math
from datetime import datetime
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from app.core.timezone import BOGOTA_TZ
from app.schemas.coreModule.order_schema import OrderFullDetailResponse

# ---------------------------------------------------------------------------
# Configuración de la empresa y del documento
# ---------------------------------------------------------------------------
COMPANY = {
    "name": "COMPAÑÍA OPITA DE FRÍO S.A.S.",
    "nit": "891.102.323-5",
    "address": "Calle 2 Sur N° 5A-09 · Neiva, Huila",
    "phones": "Tel. 873 1402 · 873 0161",
}
DEFAULT_CLIENT = {"name": "CUANTÍAS MENORES", "nit": "2222222222-9"}

LOGO_PATH = Path(__file__).parent / "assets" / "logo_foca.png"

# Paletas: "color" usa los tonos del logo; "mono" está pensada para
# impresoras térmicas (solo negro), evitando grandes bloques sólidos.
PALETTES = {
    "color": {
        "primary": colors.HexColor("#0A1A6B"),  # azul marino del logo
        "accent": colors.HexColor("#E30613"),  # rojo del logo
        "tint": colors.HexColor("#E9EEFA"),  # azul hielo
        "text": colors.HexColor("#1A1A1A"),
        "muted": colors.HexColor("#6B7280"),
        "rule": colors.HexColor("#C9D2E8"),
        "on_primary": colors.white,
    },
    "mono": {
        "primary": colors.black,
        "accent": colors.black,
        "tint": colors.HexColor("#EDEDED"),
        "text": colors.black,
        "muted": colors.HexColor("#444444"),
        "rule": colors.HexColor("#999999"),
        "on_primary": colors.white,
    },
}

# ---------------------------------------------------------------------------
# Geometría de la tirilla (80 mm)
# ---------------------------------------------------------------------------
PAGE_W = 80 * mm
MARGIN = 4 * mm
LEFT = MARGIN
RIGHT = PAGE_W - MARGIN
CENTER = PAGE_W / 2
CONTENT_W = RIGHT - LEFT

# Columnas de la tabla
COL_QTY_C = LEFT + 4 * mm  # centro de la columna CANT
COL_DESC_X = LEFT + 9 * mm  # inicio de DESCRIPCIÓN
COL_DESC_W = 32 * mm  # ancho útil de DESCRIPCIÓN
COL_UNIT_R = LEFT + 54 * mm  # borde derecho de V. UNIT
COL_TOTAL_R = RIGHT - 1.5 * mm  # borde derecho de TOTAL


def money(value) -> str:
    return f"${float(value):,.0f}".replace(",", ".")


def qty(value) -> str:
    value = float(value)
    return f"{value:,.0f}".replace(",", ".") if value.is_integer() else f"{value:,.2f}"


class PdfService:
    def __init__(self, palette: str = "color", logo_path: Path = LOGO_PATH):
        self.palette = PALETTES[palette]
        self._logo = None
        if logo_path.exists():
            img = Image.open(logo_path)
            # En térmicas el logo a color se imprime con tramado; mejor en grises.
            self._logo = ImageReader(img.convert("L") if palette == "mono" else img)

    # ------------------------------------------------------------------ API
    def generate_dispatch_receipt(self, order: OrderFullDetailResponse) -> bytes:
        # Pasada 1: se dibuja en un lienzo descartable solo para medir el alto
        # real (los nombres largos ocupan varias líneas, así que no es fijo).
        probe_h = 3000 * mm
        probe = canvas.Canvas(io.BytesIO(), pagesize=(PAGE_W, probe_h))
        used = probe_h - self._draw(probe, order, probe_h)
        page_h = used + 6 * mm

        # Pasada 2: documento definitivo con el alto exacto.
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(PAGE_W, page_h))
        c.setTitle(f"Comprobante de despacho CD-{order.purchase_order}")
        c.setAuthor(COMPANY["name"])
        self._draw(c, order, page_h)
        self._watermark(c, page_h)
        c.showPage()
        c.save()
        return buffer.getvalue()

    # ------------------------------------------------------------ secciones
    def _draw(self, c: canvas.Canvas, order, top: float) -> float:
        y = top - 6 * mm
        y = self._header(c, y)
        y = self._title_block(c, y, order)
        y = self._info_block(c, y, order)
        y = self._items_table(c, y, order)
        y = self._totals(c, y, order)
        y = self._footer(c, y)
        return y

    def _header(self, c, y):
        p = self.palette
        if self._logo:
            logo_h = 24 * mm
            iw, ih = self._logo.getSize()
            logo_w = logo_h * iw / ih
            c.drawImage(
                self._logo,
                CENTER - logo_w / 2,
                y - logo_h,
                width=logo_w,
                height=logo_h,
                mask="auto",
            )
            y -= logo_h + 4.5 * mm
        else:
            c.setFillColor(p["primary"])
            c.setFont("Helvetica-Bold", 15)
            c.drawCentredString(CENTER, y - 5 * mm, "HIELO Y AGUA FOCA")
            y -= 10 * mm

        c.setFillColor(p["primary"])
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(CENTER, y, COMPANY["name"])
        y -= 4 * mm

        c.setFillColor(p["text"])
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(CENTER, y, f"NIT {COMPANY['nit']}")
        y -= 3.3 * mm
        c.setFillColor(p["muted"])
        c.setFont("Helvetica", 7)
        c.drawCentredString(CENTER, y, COMPANY["address"])
        y -= 3.3 * mm
        c.drawCentredString(CENTER, y, COMPANY["phones"])
        y -= 4 * mm

        self._wave(c, y)
        return y - 5 * mm

    def _title_block(self, c, y, order):
        p = self.palette
        # Banda principal
        band_h = 8 * mm
        c.setFillColor(p["primary"])
        c.roundRect(LEFT, y - band_h, CONTENT_W, band_h, 1.8 * mm, stroke=0, fill=1)
        c.setFillColor(p["on_primary"])
        c.setFont("Helvetica-Bold", 10.5)
        c.drawCentredString(CENTER, y - band_h + 2.8 * mm, "COMPROBANTE DE DESPACHO")
        y -= band_h + 2.5 * mm

        # Número del comprobante
        gap_top = 3 * mm  # espacio extra respecto a la etiqueta PREVIA
        gap_bottom = 3 * mm  # espacio extra antes del recuadro de datos

        y -= gap_top
        c.setFillColor(p["muted"])
        c.setFont("Helvetica", 7)
        c.drawCentredString(CENTER, y + 0.5 * mm, "N.º")
        c.setFillColor(p["primary"])
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(CENTER, y - 5 * mm, f"CD-{order.purchase_order}")
        return y - 10 * mm - gap_bottom

    def _info_block(self, c, y, order):
        p = self.palette
        # La BD entrega el instante en UTC; se muestra en hora de Bogotá
        created: datetime = order.creation_datetime.astimezone(BOGOTA_TZ)
        dispatch = (
            order.dispatch_time.strftime("%H:%M:%S") if order.dispatch_time else "—"
        )
        rows = [
            ("Fecha", order.delivery_date.strftime("%Y-%m-%d")),
            ("Generación", created.strftime("%H:%M:%S")),
            ("Hora despacho", dispatch),
            ("Cliente", DEFAULT_CLIENT["name"]),
            ("CC / NIT", DEFAULT_CLIENT["nit"]),
            ("Conductor", (order.driver_name or "SIN ASIGNAR").upper()),
        ]

        label_x = LEFT + 3 * mm
        value_x = LEFT + 24 * mm
        value_w = RIGHT - 3 * mm - value_x
        line_h = 3.8 * mm

        # Se calculan las líneas antes de dibujar para dimensionar el recuadro
        wrapped = [
            (lbl, simpleSplit(val, "Helvetica-Bold", 7.5, value_w)) for lbl, val in rows
        ]
        box_h = sum(len(lines) for _, lines in wrapped) * line_h + 3 * mm

        c.setFillColor(p["tint"])
        c.roundRect(LEFT, y - box_h, CONTENT_W, box_h, 1.8 * mm, stroke=0, fill=1)
        c.setFillColor(p["primary"])
        c.rect(LEFT, y - box_h + 1.8 * mm, 0.9 * mm, box_h - 3.6 * mm, stroke=0, fill=1)

        ty = y - 4.2 * mm
        for i, (lbl, lines) in enumerate(wrapped):
            c.setFillColor(p["muted"])
            c.setFont("Helvetica", 7)
            c.drawString(label_x, ty, lbl)
            c.setFillColor(p["text"])
            c.setFont("Helvetica-Bold", 7.5)
            for line in lines:
                c.drawString(value_x, ty, line)
                ty -= line_h
            if i == 2:  # separador entre fechas y datos del cliente
                c.setStrokeColor(p["rule"])
                c.setLineWidth(0.4)
                c.line(
                    label_x,
                    ty + line_h - 1.3 * mm,
                    RIGHT - 3 * mm,
                    ty + line_h - 1.3 * mm,
                )
        return y - box_h - 5 * mm

    def _items_table(self, c, y, order):
        p = self.palette
        # Cabecera
        head_h = 5.5 * mm
        c.setFillColor(p["primary"])
        c.roundRect(LEFT, y - head_h, CONTENT_W, head_h, 1.2 * mm, stroke=0, fill=1)
        c.setFillColor(p["on_primary"])
        c.setFont("Helvetica-Bold", 6.8)
        hy = y - head_h + 1.9 * mm
        c.drawCentredString(COL_QTY_C, hy, "CANT")
        c.drawString(COL_DESC_X, hy, "DESCRIPCIÓN")
        c.drawRightString(COL_UNIT_R, hy, "V. UNIT")
        c.drawRightString(COL_TOTAL_R, hy, "TOTAL")
        y -= head_h

        # Filas (la descripción se ajusta en varias líneas si es larga)
        line_h = 3.4 * mm
        pad = 1.6 * mm
        for idx, item in enumerate(order.items):
            lines = simpleSplit(
                item.product_name.upper(), "Helvetica", 7.2, COL_DESC_W
            ) or [""]
            row_h = len(lines) * line_h + 2 * pad

            if idx % 2 == 1:
                c.setFillColor(p["tint"])
                c.rect(LEFT, y - row_h, CONTENT_W, row_h, stroke=0, fill=1)

            ty = y - pad - 2.5 * mm
            c.setFillColor(p["text"])
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(COL_QTY_C, ty, qty(item.cant))
            c.setFont("Helvetica", 7.2)
            for k, line in enumerate(lines):
                c.drawString(COL_DESC_X, ty - k * line_h, line)
            c.drawRightString(COL_UNIT_R, ty, money(item.unit_price))
            c.setFont("Helvetica-Bold", 7.5)
            c.drawRightString(COL_TOTAL_R, ty, money(item.subtotal))
            y -= row_h

        c.setStrokeColor(p["primary"])
        c.setLineWidth(0.8)
        c.line(LEFT, y, RIGHT, y)
        return y - 4 * mm

    def _totals(self, c, y, order):
        p = self.palette
        n_items = len(order.items)
        n_units = sum(float(i.cant) for i in order.items)

        def row(label, value, bold=False):
            nonlocal y
            c.setFillColor(p["muted"] if not bold else p["text"])
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 7.5)
            c.drawString(LEFT + 1.5 * mm, y, label)
            c.setFillColor(p["text"])
            c.drawRightString(COL_TOTAL_R, y, value)
            y -= 4 * mm

        row("Ítems", str(n_items))
        row("Unidades", qty(n_units))
        row("Subtotal", money(order.order_total), bold=True)
        y -= 1 * mm

        # Barra de total
        bar_h = 10 * mm
        bar_y = y - bar_h + 3 * mm
        c.saveState()
        clip = c.beginPath()
        clip.roundRect(LEFT, bar_y, CONTENT_W, bar_h, 1.8 * mm)
        c.clipPath(clip, stroke=0, fill=0)
        c.setFillColor(p["primary"])
        c.rect(LEFT, bar_y, CONTENT_W, bar_h, stroke=0, fill=1)
        c.setFillColor(p["accent"])
        c.rect(LEFT, bar_y, 1.4 * mm, bar_h, stroke=0, fill=1)
        c.restoreState()
        c.setFillColor(p["on_primary"])
        c.setFont("Helvetica-Bold", 8)
        c.drawString(LEFT + 4 * mm, y - bar_h / 2 + 2.2 * mm, "TOTAL A PAGAR")
        c.setFont("Helvetica-Bold", 13)
        c.drawRightString(
            COL_TOTAL_R, y - bar_h / 2 + 1.8 * mm, money(order.order_total)
        )
        return y - bar_h - 3 * mm

    def _footer(self, c, y):
        p = self.palette
        self._wave(c, y)
        y -= 6 * mm
        c.setFillColor(p["primary"])
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(CENTER, y, "¡GRACIAS POR PREFERIRNOS!")
        y -= 4.5 * mm

        note = (
            "Documento de control de despacho emitido antes de la facturación. "
            "No reemplaza la factura electrónica de venta."
        )
        c.setFillColor(p["muted"])
        c.setFont("Helvetica", 6.3)
        for line in simpleSplit(note, "Helvetica", 6.3, CONTENT_W - 6 * mm):
            c.drawCentredString(CENTER, y, line)
            y -= 2.9 * mm
        y -= 1.2 * mm
        c.setFont("Helvetica-Oblique", 6)
        c.drawCentredString(CENTER, y, f"Impreso: {datetime.now(BOGOTA_TZ):%Y-%m-%d %H:%M:%S}")
        return y

    # ----------------------------------------------------------- adornos
    def _wave(self, c, y):
        """Línea ondulada que evoca el agua del logo (azul + rojo)."""
        amp, period = 0.7 * mm, 6 * mm
        for color, dy, width in (
            (self.palette["primary"], 0, 1.1),
            (self.palette["accent"], -1.6 * mm, 0.6),
        ):
            path = c.beginPath()
            x = LEFT
            path.moveTo(x, y + dy)
            while x <= RIGHT:
                path.lineTo(
                    x, y + dy + amp * math.sin((x - LEFT) / period * 2 * math.pi)
                )
                x += 0.4 * mm
            c.setStrokeColor(color)
            c.setLineWidth(width)
            c.drawPath(path, stroke=1, fill=0)

    def _watermark(self, c, page_h):
        c.saveState()
        c.setFillColor(self.palette["primary"])
        c.setFillAlpha(0.06)
        c.setFont("Helvetica-Bold", 44)
        c.translate(CENTER, page_h * 0.45)
        c.rotate(55)
        c.drawCentredString(0, -15, "DESPACHADO")
        c.restoreState()


pdf_service = PdfService()
