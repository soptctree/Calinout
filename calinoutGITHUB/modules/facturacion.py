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
    
    # 3. TOTAL FINAL (Corregido: Solo aparece una vez)
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

    # .encode('latin-1', 'replace') para evitar errores con caracteres especiales
    pdf_output = pdf.output()
    return bytes(pdf_output) if isinstance(pdf_output, bytearray) else pdf_output.encode('latin-1', errors='replace')

def render_tab_facturacion():
    st.header("🧾 Módulo de Facturación Pro")

    # 1. INICIALIZACIÓN DE ESTADO (Evita errores de variable no definida)
    if "factura_generada" not in st.session_state:
        st.session_state.factura_generada = False

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Traemos también el campo de adultos (asumiendo que se llama 'adultos' en tu tabla)
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

    opciones = {f"Reserva #{r['id_reserva']} - {r['nombre_huesped']}": r['id_reserva'] for r in reservas_pendientes}
    res_sel_text = st.selectbox("Seleccione la reserva a facturar:", options=list(opciones.keys()))
    id_sel = opciones[res_sel_text]
    
    res = next(r for r in reservas_pendientes if r['id_reserva'] == id_sel)

    if res:
        # --- CÁLCULOS BASE (Ubicados aquí para que siempre existan antes de la UI) ---
        noches = (res['fecha_salida'] - res['fecha_entrada']).days
        # Si 'adultos' no existe en tu tabla, cámbialo por el nombre correcto o usa 1 por defecto
        adultos = res.get('adultos', 1) 
        
        st.divider()
        
        col_res, col_adj, col_totales = st.columns([1, 1.2, 1])

        with col_res:
            st.markdown("##### 📋 Datos de Estancia")
            with st.container(border=True):
                st.markdown(f"""
                **Huésped Principal:** {res['nombre_huesped']}  
                **Adultos:** {adultos} | **Niños:** {res['ninos']}  
                **Unidad:** {res['nombre_personalizado']}  
                **Noches:** {noches}  
                **Periodo:** {res['fecha_entrada']} / {res['fecha_salida']}
                """)
            
            if st.session_state.factura_generada:
                st.text_area("Nota especial:", value=st.session_state.get('last_nota', ""), disabled=True, height=100)
            else:
                # Usamos una clave única para el widget para evitar conflictos
                nota_factura = st.text_area("Nota especial:", placeholder="Ej: Tour, desayuno...", height=100, key="nota_input")

        with col_adj:
            st.markdown("##### 💰 Ajustes y Extras")
            
            if not st.session_state.factura_generada:
                p_noche = st.number_input("Precio/Noche ($)", value=float(res['precio_noche']))
                
                c1, c2 = st.columns(2)
                with c1:
                    # Cálculo automático sugerido: $10 por niño por noche
                    valor_sugerido_nino = float(res['ninos'] * 10.0 * noches)
                    cargo_ninos = st.number_input(f"Extras Niños ({res['ninos']})", value=valor_sugerido_nino)
                    extra_servicios = st.number_input("Otros Extras", value=0.0)
                with c2:
                    # Cálculo automático sugerido: $15 por mascota por noche
                    cargo_mascotas = st.number_input(f"Extras Mascotas ({res['mascotas']})", value=float(res['mascotas'] * 15.0 * noches))
                    st.write("") 
                    aplicar_propina = st.checkbox("¿Propina 10%?")
                
                # CÁLCULOS MATEMÁTICOS (Siempre dentro del bloque de edición)
                subtotal_estancia = noches * p_noche
                subtotal_servicios = subtotal_estancia + cargo_ninos + cargo_mascotas + extra_servicios
                iva = subtotal_servicios * (float(res.get('impuestos_porcentaje', 15)) / 100)
                propina = (subtotal_servicios + iva) * 0.10 if aplicar_propina else 0.0
                total_a_cobrar = subtotal_servicios + iva + propina
            
            else:
                # MODO LECTURA: Recuperamos valores del session_state para evitar errores
                with st.container(border=True):
                    st.write(f"**Precio Noche:** ${st.session_state.last_p_noche:.2f}")
                    st.write(f"**Extras Niños:** ${st.session_state.last_cargo_ninos:.2f}")
                    st.write(f"**Extras Mascotas:** ${st.session_state.last_cargo_mascotas:.2f}")
                    st.write(f"**Otros Servicios:** ${st.session_state.last_extra_servicios:.2f}")
                    total_a_cobrar = st.session_state.last_total

        with col_totales:
            st.markdown("##### 💵 Resumen de Pago")
            with st.container(border=True):
                if not st.session_state.factura_generada:
                    st.write(f"**Subtotal:** ${subtotal_servicios:.2f}")
                    st.write(f"**IVA:** ${iva:.2f}")
                    if propina > 0: st.write(f"**Propina:** ${propina:.2f}")
                    st.divider()
                    st.metric("TOTAL A COBRAR", f"${total_a_cobrar:.2f}")
                else:
                    st.write(f"**Subtotal:** ${st.session_state.last_subtotal:.2f}")
                    st.write(f"**IVA:** ${st.session_state.last_iva:.2f}")
                    if st.session_state.last_propina > 0: st.write(f"**Propina:** ${st.session_state.last_propina:.2f}")
                    st.divider()
                    st.metric("PAGO PROCESADO", f"${st.session_state.last_total:.2f}")

            # --- LÓGICA DE CONTROL ---
            if not st.session_state.factura_generada:
                if st.button("🚀 Generar Factura y Procesar Datos", use_container_width=True, type="primary"):
                    # CONGELAMOS LOS DATOS
                    st.session_state.last_p_noche = p_noche
                    st.session_state.last_cargo_ninos = cargo_ninos
                    st.session_state.last_cargo_mascotas = cargo_mascotas
                    st.session_state.last_extra_servicios = extra_servicios
                    st.session_state.last_subtotal = subtotal_servicios
                    st.session_state.last_iva = iva
                    st.session_state.last_propina = propina
                    st.session_state.last_total = total_a_cobrar
                    st.session_state.last_nota = nota_factura
                    
                    st.session_state.factura_generada = True
                    st.rerun() 
            else:
                # PDF usando datos congelados
                datos_factura = {
                    "id_reserva": res['id_reserva'], 
                    "nombre_huesped": res['nombre_huesped'],
                    "nombre_personalizado": res['nombre_personalizado'], 
                    "fecha_entrada": res['fecha_entrada'],
                    "fecha_salida": res['fecha_salida'], 
                    "noches": noches, 
                    "adultos": adultos, # Agregamos adultos al PDF
                    "ninos": res['ninos'],
                    "mascotas": res['mascotas'], 
                    "subtotal_estancia": (noches * st.session_state.last_p_noche),
                    "cargo_ninos": st.session_state.last_cargo_ninos, 
                    "cargo_mascotas": st.session_state.last_cargo_mascotas,
                    "extra_servicios": st.session_state.last_extra_servicios, 
                    "nota_factura": st.session_state.last_nota,
                    "iva": st.session_state.last_iva, 
                    "propina": st.session_state.last_propina, 
                    "total_a_cobrar": st.session_state.last_total
                }
                pdf_bytes = generar_pdf_factura(datos_factura)

                st.success("✅ Pago procesado")
                st.download_button("📥 Descargar PDF", data=pdf_bytes, file_name=f"Factura_{res['nombre_huesped']}.pdf", mime="application/pdf", use_container_width=True)

                if st.button("🏁 Finalizar y Nueva Consulta", use_container_width=True):
                    try:
                        conn = get_connection(); cursor = conn.cursor()
                        cursor.execute("UPDATE reservas SET estado_pago = 'Pagado' WHERE id_reserva = %s", (res['id_reserva'],))
                        conn.commit()
                        st.session_state.factura_generada = False 
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Error: {e}")
