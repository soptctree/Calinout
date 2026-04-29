import streamlit as st
from database import get_connection
from fpdf import FPDF
import io

def generar_pdf_factura(datos):
    # Configuración de página Carta (Letter)
    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.add_page()
    pdf.set_margins(15, 20, 15)
    
    azul_oscuro = (26, 64, 107)
    azul_claro = (210, 225, 245)
    gris_suave = (245, 245, 245)
    
    # --- ENCABEZADO ---
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(*azul_oscuro)
    pdf.cell(100, 15, "FACTURA DE SERVICIO", 0, 0)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "HOSTAL ALEGRIA", 0, 1, 'R')
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(100)
    pdf.cell(0, 5, "Ometepe, Nicaragua", 0, 1, 'R')
    pdf.cell(0, 5, "RUC:5702802970000k", 0, 1, 'R')
    pdf.ln(10)
    
    # --- INFORMACIÓN DE LA RESERVA ---
    pdf.set_fill_color(*azul_claro)
    pdf.set_text_color(0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, " DATOS DE LA RESERVA", 1, 1, 'L', True)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(35, 10, " Huesped:", "LB", 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(90, 10, f" {datos['nombre_huesped']}", "RB", 0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 10, " Reserva:", "LB", 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f" #00{datos.get('id_reserva', '35')}", "RB", 1)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(35, 10, " Check In:", "LB", 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(90, 10, f" {datos['fecha_entrada']}", "RB", 0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 10, " Check Out:", "LB", 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f" {datos['fecha_salida']}", "RB", 1)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(35, 10, " Unidad/Casa:", "LB", 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f" {datos.get('nombre_personalizado', 'Habitacion Estandar')}", "RB", 1)
    pdf.ln(10)

    # --- TABLA DE DETALLES ---
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(*azul_claro)
    pdf.cell(110, 12, " Descripcion", 1, 0, 'C', True)
    pdf.cell(26, 12, " Cant", 1, 0, 'C', True)
    pdf.cell(50, 12, " Importe", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 11)
    
    # 1. Hospedaje
    pdf.cell(110, 10, f" Hospedaje ({datos.get('nombre_personalizado', 'Estandar')})", 1, 0, 'L')
    pdf.cell(26, 10, f" {datos['noches']}", 1, 0, 'C')
    pdf.cell(50, 10, f" ${datos['subtotal_estancia']:.2f}", 1, 1, 'R')

    # 2. Suplemento Niños
    if datos.get('cargo_ninos', 0) > 0:
        pdf.cell(110, 10, f" Ninos", 1, 0, 'L')
        pdf.cell(26, 10, f" {datos.get('ninos', 0)}", 1, 0, 'C')
        pdf.cell(50, 10, f" ${datos['cargo_ninos']:.2f}", 1, 1, 'R')

    # 3. Suplemento Mascotas
    if datos.get('cargo_mascotas', 0) > 0:
        pdf.cell(110, 10, f" Mascotas", 1, 0, 'L')
        pdf.cell(26, 10, f" {datos.get('mascotas', 0)}", 1, 0, 'C')
        pdf.cell(50, 10, f" ${datos['cargo_mascotas']:.2f}", 1, 1, 'R')

    # 4. Otros Servicios
    if datos.get('extra_servicios', 0) > 0:
        desc_extra = datos.get('nota_factura', 'Otros servicios')
        if not desc_extra or not desc_extra.strip(): desc_extra = "Otros servicios"
        pdf.cell(110, 10, f" Extra: {desc_extra}", 1, 0, 'L')
        pdf.cell(26, 10, "-", 1, 0, 'C')
        pdf.cell(50, 10, f" ${datos['extra_servicios']:.2f}", 1, 1, 'R')

    # --- FILA DE SUB-TOTAL ---
    subtotal_antes_iva = datos['subtotal_estancia'] + datos.get('cargo_ninos', 0) + datos.get('cargo_mascotas', 0) + datos.get('extra_servicios', 0)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(*gris_suave)
    pdf.cell(136, 10, " SUB-TOTAL SERVICIOS", 1, 0, 'R', True)
    pdf.cell(50, 10, f" ${subtotal_antes_iva:.2f}", 1, 1, 'R', True)

    # --- TOTALES FINALES ---
    pdf.ln(2)
    pdf.set_x(121)
    pdf.set_font("Arial", 'B', 10)
    
    # 1. IVA
    pdf.cell(40, 8, " IVA (15%)", 1, 0, 'L', True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(35, 8, f" ${datos['iva']:.2f}", 1, 1, 'R')
    
    # 2. PROPINA
    if datos.get('propina', 0) > 0:
        pdf.set_x(121)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 8, " Propina (10%)", 1, 0, 'L', True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(35, 8, f" ${datos['propina']:.2f}", 1, 1, 'R')
    
    # 3. TOTAL FINAL
    pdf.set_x(121)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(*azul_claro)
    pdf.cell(40, 10, " TOTAL USD", 1, 0, 'L', True)
    pdf.cell(35, 10, f" ${datos['total_a_cobrar']:.2f}", 1, 1, 'R')

    # --- PIE DE PÁGINA ---
    pdf.set_y(-45)
    pdf.set_font("Arial", 'B', 8)
    pdf.set_text_color(100)
    pdf.cell(0, 5, "TERMINOS Y CONDICIONES:", 0, 1)
    pdf.set_font("Arial", '', 8)
    pdf.multi_cell(0, 4, (
        "- Check-in 2:00 PM / Check-out 11:00 AM.\n"
        "- Respetar el silencio despues de las 10:00 PM.\n"
        "- No se permite musica con alto volumen en areas comunes.\n"
        "- Cancelaciones: Menos de 48 horas no aplica reembolso."
    ))

    # CORRECCIÓN AQUÍ: Se eliminó el .encode('latin-1') que causaba el error en Python 3.14
    return pdf.output()

def render_tab_facturacion():
    st.header("🧾 Módulo de Facturación Pro")

    if "factura_generada" not in st.session_state:
        st.session_state.factura_generada = False

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.*, n.nombre_personalizado 
            FROM reservas r
            JOIN nombres_casas n ON r.id_casa = n.id_casa
            WHERE r.estado_pago != 'Pagado'
        """)
        reservas_pendientes = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Error al cargar facturas: {e}")
        return

    if not reservas_pendientes:
        st.info("No hay facturas pendientes.")
        return

    opciones = {f"Reserva #{r['id_reserva']} - {r['nombre_huesped']}": r['id_
