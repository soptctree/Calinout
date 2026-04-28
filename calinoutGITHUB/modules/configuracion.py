import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime

# En modules/configuracion.py o una pestaña nueva de Admin
def seccion_admin_costos():
    st.header("📋 Ficha Técnica de Costos Operativos")
    st.caption("Solo accesible para Administradores. Configure los costos base de cada unidad.")

    # Obtenemos las casas de la base de datos
    conn = get_connection()
    df_villas = pd.read_sql("SELECT id_casa, nombre_personalizado FROM nombres_casas", conn)
    
    opciones_villas = {row['nombre_personalizado']: row['id_casa'] for _, row in df_villas.iterrows()}
    seleccionada = st.selectbox("Seleccione unidad a costear:", opciones_villas.keys())
    id_v_sel = opciones_villas[seleccionada]

    with st.form("form_ficha_tecnica"):
        c1, c2 = st.columns(2)
        with c1:
            limpieza = st.number_input("Costo Limpieza/Lavandería (Fijo x Estancia)", min_value=0.0, step=1.0)
            amenities = st.number_input("Amenities/Consumibles (Por Persona)", min_value=0.0, step=1.0)
        with c2:
            energia = st.number_input("Energía/Agua (Promedio x Noche)", min_value=0.0, step=1.0)
            comision = st.number_input("% Comisión Plataforma (Si aplica)", min_value=0.0, max_value=100.0)

        if st.form_submit_button("Guardar Ficha Técnica"):
            # Lógica para INSERT ... ON DUPLICATE KEY UPDATE
            cursor = conn.cursor()
            sql = """
                INSERT INTO ficha_tecnica_costos (id_casa, costo_limpieza_fijo, costo_amenities_pax, costo_energia_noche, comision_plataforma_porc)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                costo_limpieza_fijo=%s, costo_amenities_pax=%s, costo_energia_noche=%s, comision_plataforma_porc=%s
            """
            vals = (id_v_sel, limpieza, amenities, energia, comision, limpieza, amenities, energia, comision)
            cursor.execute(sql, vals)
            conn.commit()
            st.success(f"✅ Ficha técnica de {seleccionada} actualizada.")
    
    conn.close()
    # Retornamos los valores para que el panel de tarifas pueda usarlos
    costo_total = limpieza + (amenities * 2) + energia
    return id_v_sel, costo_total

def render_tab_configuracion():
    st.header("⚙️ Configuración del Sistema")
    
    # 1. Ejecutamos la sección de costos y capturamos sus datos
    id_casa_sel, costo_base = seccion_admin_costos()
    
    # 2. Pasamos esos datos al panel de tarifas
    panel_tarifas_gerencia(id_casa_sel, costo_base)
    
    # --- 3. PESTAÑAS PRINCIPALES ---
    subtab1, subtab2 = st.tabs(["🏡 Gestión de Habitaciones", "🛠️ Mantenimiento y Bloqueos"])
    
    with subtab1:
        st.subheader("Panel de Propiedades")
        st.info("Añade nuevas habitaciones o edita las existentes. Las archivadas no aparecerán en el calendario.")

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)

            # --- A. AGREGAR NUEVA CASA ---
            with st.expander("➕ Registrar Nueva Habitación", expanded=False):
                with st.form("nueva_casa_form", clear_on_submit=True):
                    cursor.execute("SELECT MAX(id_casa) as max_id FROM nombres_casas")
                    res_max = cursor.fetchone()
                    ultimo_id = res_max['max_id'] if res_max else 0
                    siguiente_id = (ultimo_id or 0) + 1
                    
                    st.write(f"Se registrará como **ID: {siguiente_id}**")
                    nuevo_nombre = st.text_input("Nombre de la Habitación:", placeholder="Ej: Villa Atardecer")
                    
                    if st.form_submit_button("Guardar Habitación"):
                        if nuevo_nombre:
                            cursor.execute(
                                "INSERT INTO nombres_casas (id_casa, nombre_personalizado, activo) VALUES (%s, %s, 1)",
                                (siguiente_id, nuevo_nombre)
                            )
                            conn.commit()
                            st.success(f"✅ ¡{nuevo_nombre} agregada!") 
                            st.rerun()
                        else:
                            st.warning("⚠️ Escribe un nombre para la casa.")

            st.divider()

            # --- B. LISTADO Y EDICIÓN ---
            cursor.execute("SELECT * FROM nombres_casas ORDER BY id_casa ASC")
            casas_existentes = cursor.fetchall()

            for casa in casas_existentes:
                id_c, nom_c, esta_activa = casa['id_casa'], casa['nombre_personalizado'], casa['activo']
                col_id, col_nom, col_btn = st.columns([1, 3, 2])
                
                with col_id:
                    st.write(f"**#{id_c}**")
                
                with col_nom:
                    if not esta_activa:
                        st.text_input(f"Nombre {id_c}", value=nom_c, key=f"in_{id_c}", disabled=True, label_visibility="collapsed")
                        st.caption(f"🚫 Archivada")
                    else:
                        nuevo_nom = st.text_input(f"Nombre {id_c}", value=nom_c, key=f"in_{id_c}", label_visibility="collapsed")
                
                with col_btn:
                    b1, b2 = st.columns(2)
                    if esta_activa:
                        if b1.button("💾", key=f"save_{id_c}"):
                            cursor.execute("UPDATE nombres_casas SET nombre_personalizado = %s WHERE id_casa = %s", (nuevo_nom, id_c))
                            conn.commit()
                            st.rerun()
                        if b2.button("🗑️", key=f"del_{id_c}"):
                            cursor.execute("UPDATE nombres_casas SET activo = 0 WHERE id_casa = %s", (id_c,))
                            conn.commit()
                            st.rerun()
                    else:
                        if b2.button("♻️", key=f"react_{id_c}"):
                            cursor.execute("UPDATE nombres_casas SET activo = 1 WHERE id_casa = %s", (id_c,))
                            conn.commit()
                            st.rerun()

        except Exception as e:
            st.error(f"Error en Gestión de Villas: {e}")
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()

    with subtab2:
        st.subheader("Bloqueo Temporal de Unidades")
        st.info("Marca unidades fuera de servicio por limpieza o reparaciones.")
        
        with st.form("form_bloqueo"):
            villa_bloqueo = st.selectbox("Seleccionar Unidad:", ["Villa Ometepe", "Cabaña Maderas"])
            rango_bloqueo = st.date_input("Rango de Bloqueo:", value=None)
            motivo = st.text_input("Motivo:", placeholder="Ej: Reparación AA")
            
            if st.form_submit_button("Aplicar Bloqueo"):
                st.success(f"La unidad {villa_bloqueo} ha sido bloqueada.")

def panel_tarifas_gerencia(id_v_sel, costo_operativo_base):
    st.markdown("---")
    st.subheader("📝 Definición de Tarifas Autorizadas")
    st.info(f"Costo Operativo Base: ${costo_operativo_base:.2f}")

    with st.form("form_tarifas_oficiales"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            t_promo = st.number_input("Tarifa Baja / Promo", min_value=costo_operativo_base)
            m_p = ((t_promo - costo_operativo_base) / t_promo * 100) if t_promo > 0 else 0
            st.caption(f"Margen: {m_p:.1f}%")

        with col2:
            t_std = st.number_input("Tarifa Estándar", min_value=costo_operativo_base)
            m_s = ((t_std - costo_operativo_base) / t_std * 100) if t_std > 0 else 0
            st.caption(f"Margen: {m_s:.1f}%")

        with col3:
            t_high = st.number_input("Tarifa Alta / Peak", min_value=costo_operativo_base)
            m_a = ((t_high - costo_operativo_base) / t_high * 100) if t_high > 0 else 0
            st.caption(f"Margen: {m_a:.1f}%")

        if st.form_submit_button("Aprobar y Publicar Tarifas"):
            st.success("✅ Tarifas publicadas. El recepcionista ahora puede seleccionarlas.")