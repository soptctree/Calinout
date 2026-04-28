import streamlit as st
from database import get_connection
from datetime import timedelta

def obtener_tarifas_config():
    """Trae las tarifas dinámicas desde la tabla de configuración."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT tarifa_nino, tarifa_mascota, impuesto_base FROM configuracion_tarifas WHERE id = 1")
        config = cursor.fetchone()
        cursor.close()
        conn.close()
        if config:
            return config
        return {"tarifa_nino": 10.0, "tarifa_mascota": 15.0, "impuesto_base": 15.0}
    except Exception as e:
        # Registramos el error en consola para depurar sin romper la app
        print(f"Error en configuración: {e}")
        return {"tarifa_nino": 10.0, "tarifa_mascota": 15.0, "impuesto_base": 15.0}

def render_tab_reservas():
    st.header("🏨 Registro de Nuevas Reservas")
    
    # Cargar configuraciones de la base de datos
    conf = obtener_tarifas_config()
    
    # 1. Obtener lista de casas activas
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_casa, nombre_personalizado FROM nombres_casas WHERE activo = 1")
        villas = cursor.fetchall()
        lista_nombres = [v['nombre_personalizado'] for v in villas]
        dict_villas = {v['nombre_personalizado']: v['id_casa'] for v in villas}
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Error al cargar unidades: {e}")
        return

    # 2. Formulario Pro con Cálculos Variables
    with st.form("form_reserva_premium", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("👤 Datos del Huésped")
            nombre = st.text_input("Nombre completo")
            villa_sel = st.selectbox("Unidad / Casa", lista_nombres)
            periodo = st.date_input("Fechas de Estancia", value=[])
            
        with col_b:
            st.subheader("👥 Cargos Variables")
            c_n, c_m = st.columns(2)
            with c_n: ninos = st.number_input(f"Niños (${conf['tarifa_nino']}/noche)", min_value=0)
            with c_m: mascotas = st.number_input(f"Mascotas (${conf['tarifa_mascota']}/noche)", min_value=0)
            
            st.write("---")
            st.subheader("💰 Tarifa Base")
            precio_n = st.number_input("Precio Habitación por Noche ($)", min_value=0.0, value=80.0)
            adultos = st.number_input("Adultos", min_value=1, value=1)

        notas = st.text_area("Notas especiales o servicios extra")
        est_pago = st.selectbox("Estado inicial de pago", ["Pendiente", "Parcial", "Pagado"])

        # --- RESUMEN DINÁMICO EN TIEMPO REAL ---
        total_final = 0.0
        noches = 0
        if len(periodo) == 2:
            f_in, f_out = periodo
            noches = (f_out - f_in).days
            if noches > 0:
                costo_hospedaje = noches * precio_n
                extra_ninos = noches * ninos * float(conf['tarifa_nino'])
                extra_mascotas = noches * mascotas * float(conf['tarifa_mascota'])
                
                subtotal = costo_hospedaje + extra_ninos + extra_mascotas
                impuesto = subtotal * (float(conf['impuesto_base']) / 100)
                total_final = subtotal + impuesto
                
                st.info(f"""
                📊 **Desglose de Estancia ({noches} noches):**
                - Hospedaje Base: **${costo_hospedaje:.2f}**
                - Suplemento Niños: **${extra_ninos:.2f}**
                - Suplemento Mascotas: **${extra_mascotas:.2f}**
                - Impuestos ({conf['impuesto_base']}%): **${impuesto:.2f}**
                - **TOTAL ESTIMADO: ${total_final:.2f}**
                """)
            elif (f_out - f_in).days <= 0 and len(periodo) == 2:
                st.warning("⚠️ La fecha de salida debe ser después de la entrada.")

        submit = st.form_submit_button("Confirmar Reserva")

    # 3. Guardado en Base de Datos con Validaciones Extra
    if submit:
        if not nombre:
            st.warning("Por favor, ingrese el nombre del huésped.")
        elif len(periodo) != 2:
            st.warning("Por favor, seleccione un rango de fechas válido.")
        else:
            id_casa = dict_villas[villa_sel]
            f_in, f_out = periodo
            
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                
                # --- MEJORA 1: VALIDACIÓN DE CHOQUE CON OTRAS RESERVAS ---
                sql_val_res = "SELECT id_reserva FROM reservas WHERE id_casa = %s AND %s < fecha_salida AND %s > fecha_entrada"
                cursor.execute(sql_val_res, (id_casa, f_in, f_out))
                hay_reserva = cursor.fetchone()
                
                # --- MEJORA 2: VALIDACIÓN DE CHOQUE CON BLOQUEOS MANUALES (TABLA OCUPACION) ---
                # Verificamos si algún día del rango está marcado como Bloqueado o Mantenimiento
                sql_val_bloq = "SELECT estado FROM ocupacion WHERE id_casa = %s AND fecha >= %s AND fecha < %s AND estado != 'Libre'"
                cursor.execute(sql_val_bloq, (id_casa, f_in, f_out))
                hay_bloqueo = cursor.fetchone()
                
                if hay_reserva:
                    st.error("⚠️ Error: La unidad ya tiene una reserva confirmada en esas fechas.")
                elif hay_bloqueo:
                    st.error(f"🚫 Error: La unidad está bloqueada por: **{hay_bloqueo['estado']}**")
                else:
                    # Si todo está libre, procedemos al INSERT
                    sql_ins = """
                        INSERT INTO reservas 
                        (id_casa, nombre_huesped, fecha_entrada, fecha_salida, adultos, ninos, mascotas, 
                         precio_noche, extras_total, impuestos_porcentaje, estado_pago, notas)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    extras_db = (noches * ninos * float(conf['tarifa_nino'])) + (noches * mascotas * float(conf['tarifa_mascota']))
                    
                    valores = (id_casa, nombre, f_in, f_out, adultos, ninos, mascotas, 
                               precio_n, extras_db, conf['impuesto_base'], est_pago, notas)
                    
                    cursor.execute(sql_ins, valores)
                    conn.commit()
                    
                    st.success(f"✅ Reserva guardada con éxito para {nombre}.")
                    st.balloons()
                    st.rerun()
                
                cursor.close()
                conn.close()
            except Exception as e:
                st.error(f"Error técnico al procesar reserva: {e}")