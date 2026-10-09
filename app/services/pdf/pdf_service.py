import io

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.schemas.coreModule.order_schema import OrderFullDetailResponse


class PdfService:
    def generate_dispatch_receipt(self, order: OrderFullDetailResponse) -> bytes:
        buffer = io.BytesIO()

        # --- 1. Cálculo dinámico del alto de la tirilla (Ancho fijo: 80mm) ---
        base_height = 130 * mm  # Alto para encabezado, info de cliente y totales
        item_row_height = 5 * mm  # Alto por cada producto en la tabla
        total_height = base_height + (len(order.items) * item_row_height)

        # Crear el lienzo (Canvas)
        c = canvas.Canvas(buffer, pagesize=(80 * mm, total_height))

        # Punto de inicio en el eje Y (Arriba hacia abajo)
        y = total_height - 10 * mm

        # --- 2. Encabezado y Logo ---
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(40 * mm, y, "HIELO Y AGUA FOCA")
        y -= 5 * mm

        c.setFont("Helvetica", 9)
        c.drawCentredString(40 * mm, y, "COMPAÑIA OPITA DE FRIO S.A.S.")
        y -= 4 * mm
        c.drawCentredString(40 * mm, y, "NIT.: 891.102.323-5")
        y -= 6 * mm

        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(40 * mm, y, "COMPROBANTE DE DESPACHO")
        y -= 4 * mm
        c.drawCentredString(40 * mm, y, f"CD - {order.purchase_order}")
        y -= 8 * mm

        # --- 3. Fechas ---
        c.setFont("Helvetica", 8)
        c.drawString(
            5 * mm,
            y,
            f"Generación: {order.creation_datetime.strftime('%Y-%m-%d %H:%M:%S')}",
        )
        y -= 4 * mm
        # Manejamos el caso de que dispatch_time sea solo un objeto time
        dispatch_str = (
            order.dispatch_time.strftime("%H:%M:%S") if order.dispatch_time else ""
        )
        c.drawString(
            5 * mm,
            y,
            f"Expedición: {order.creation_datetime.strftime('%Y-%m-%d')} {dispatch_str}",
        )
        y -= 8 * mm

        # --- 4. Información Estática (Cuantías Menores) y Vendedor ---
        c.setFont("Helvetica-Bold", 8)
        c.drawString(5 * mm, y, "Cliente:")
        c.setFont("Helvetica", 8)
        c.drawString(20 * mm, y, "CUANTIAS MENORES")
        y -= 4 * mm

        c.setFont("Helvetica-Bold", 8)
        c.drawString(5 * mm, y, "CC/NIT:")
        c.setFont("Helvetica", 8)
        c.drawString(20 * mm, y, "2222222222 - 9")
        y -= 4 * mm

        c.setFont("Helvetica-Bold", 8)
        c.drawString(5 * mm, y, "Vendedor:")
        c.setFont("Helvetica", 8)
        driver_name = order.driver_name if order.driver_name else "SIN ASIGNAR"
        c.drawString(20 * mm, y, driver_name)
        y -= 8 * mm

        # --- 5. Cabecera de la Tabla de Productos ---
        c.setFont("Helvetica-Bold", 8)
        c.drawString(5 * mm, y, "CANT")
        c.drawString(18 * mm, y, "DESCRIPCION")
        c.drawString(50 * mm, y, "V.UNIT")
        c.drawString(65 * mm, y, "TOTAL")
        y -= 2 * mm
        c.line(5 * mm, y, 75 * mm, y)  # Línea divisoria
        y -= 4 * mm

        # --- 6. Filas de Productos ---
        c.setFont("Helvetica", 8)
        for item in order.items:
            c.drawString(5 * mm, y, str(item.cant))
            # Truncamos el nombre del producto si es muy largo (máx 15 caracteres)
            c.drawString(18 * mm, y, item.product_name[:15])
            c.drawString(50 * mm, y, f"${item.unit_price:,.0f}".replace(",", "."))
            c.drawString(65 * mm, y, f"${item.subtotal:,.0f}".replace(",", "."))
            y -= item_row_height

        y += 2 * mm
        c.line(5 * mm, y, 75 * mm, y)  # Línea divisoria
        y -= 5 * mm

        # --- 7. Total ---
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y, "TOTAL A PAGAR:")
        c.drawString(65 * mm, y, f"${order.order_total:,.0f}".replace(",", "."))

        # --- Finalizar ---
        c.showPage()
        c.save()
        return buffer.getvalue()


pdf_service = PdfService()
