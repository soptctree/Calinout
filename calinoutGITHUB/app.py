import streamlit as st
import sys
import os
from datetime import date, timedelta

# 1. SIEMPRE debe ser la primera instrucción de Streamlit
st.set_page_config(page_title="Calinout Pro", layout="wide")

# 2. Configuración de rutas
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.append(root_path)

# 3. Importaciones unificadas
from database import get_connection

try:
    from modules.calendario import render_tab_calendario, render_tab_inclusiones
    from modules.reservas import render_tab_reservas
    from modules.facturacion import render_tab_facturacion
    from modules.auditoria import render_tab_auditoria
    from modules.configuracion import render_tab_configuracion, seccion_admin_costos
    from modules.contabilidad import render_tab_contabilidad
except ImportError as e:
    st.error(f"⚠️ Error cargando módulos: {e}")

# Gestión de estado
if "factura_generada" not in st.session_state:
    st.session_state.factura_generada = False

# --- LÓGICA DE DATOS ---
def obtener_nombres_villas():
    try:
        conn = get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # OJO: Asegúrate que en TiDB la columna se llame 'nombre_personalizado'
            cursor.execute("SELECT nombre_personalizado FROM nombres_casas WHERE activo = 1")
            villas = [row['nombre_personalizado'] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return villas
        return ["Villa 1", "Villa 2"] # Respaldo si no hay conexión
    except Exception as e:
        return ["Villa 1", "Villa 2"]

lista_villas = obtener_nombres_villas()
hoy = date.today()

# --- SIDEBAR (LOGIN Y FILTROS) ---
with st.sidebar:
    st.title("🔐 Control de Acceso")
    usuario_simulado = st.selectbox(
        "Iniciar sesión como:",
        ["Recepcionista (Limitado)", "Contador (Finanzas)", "Admin (Acceso Total)"]
    )

    if "Admin" in usuario_simulado:
        st.session_state.rol = "admin"
    elif "Contador" in usuario_simulado:
        st.session_state.rol = "contador"
    else:
        st.session_state.rol = "recepcionista"

    st.divider()
    st.title("🏨 Calinout Pro")
    
    casa_global = st.multiselect(
        "Filtrar por Casa", 
        options=lista_villas,
        default=[], 
        placeholder="Todas las unidades",
        key="selector_casas_multiple"
    )

    periodo_global = st.date_input(
        "Rango de Visualización", 
        value=[hoy, hoy + timedelta(days=7)]
    )
    
    st.divider()
    
    # Gestión de Estado (Bloqueos)
    st.subheader("🛠️ Gestión de Estado")
    with st.expander("Bloquear/Desbloquear"):
        with st.form("form_bloqueo_sidebar", clear_on_submit=True):
            v_bloqueo = st.selectbox("Unidad", lista_villas)
            f_bloqueo = st.date_input("Fecha", value=hoy)
            nuevo_estado = st.selectbox("Nuevo Estado", ["Libre", "Bloqueado", "Mantenimiento"])
            submit_bloqueo = st.form_submit_button("Actualizar")

        if submit_bloqueo:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                sql_update = """
                    INSERT INTO ocupacion (id_casa, fecha, estado)
                    VALUES ((SELECT id_casa FROM nombres_casas WHERE nombre_personalizado = %s), %s, %s)
                    ON DUPLICATE KEY UPDATE estado = %s
                """
                cursor.execute(sql_update, (v_bloqueo, f_bloqueo, nuevo_estado, nuevo_estado))
                conn.commit()
                st.success(f"✅ {v_bloqueo} actualizado")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                if conn: conn.close()

# --- RENDERIZADO DE PESTAÑAS SEGÚN ROL ---
if st.session_state.rol == "admin":
    nombres = ["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📊 Auditoría", "📋 Inclusiones", "💰 Contabilidad", "⚙️ Configuración"]
    tabs = st.tabs(nombres)
    with tabs[0]: render_tab_calendario(periodo_global, casa_global)
    with tabs[1]: render_tab_reservas()
    with tabs[2]: render_tab_facturacion()
    with tabs[3]: render_tab_auditoria()
    with tabs[4]: render_tab_inclusiones()
    with tabs[5]: render_tab_contabilidad()
    with tabs[6]: render_tab_configuracion()

elif st.session_state.rol == "contador":
    nombres = ["🧾 Facturación", "📊 Auditoría", "💰 Contabilidad"]
    tabs = st.tabs(nombres)
    with tabs[0]: render_tab_facturacion()
    with tabs[1]: render_tab_auditoria()
    with tabs[2]: render_tab_contabilidad()

else: # Recepcionista
    nombres = ["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📋 Inclusiones"]
    tabs = st.tabs(nombres)
    with tabs[0]: render_tab_calendario(periodo_global, casa_global)
    with tabs[1]: render_tab_reservas()
    with tabs[2]: render_tab_facturacion()
    with tabs[3]: render_tab_inclusiones()
#######XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX######################
# --- PESTAÑAS PRINCIPALES (FUERA DEL SIDEBAR) ---
#tab1, tab2, tab3, tab4, tab5,tab6 = st.tabs([
    #"📅 Calendario", "🏨 Reservas", "🧾 Facturación", "📊 Auditoría", "⚙️ Configuración","💰 Contabilidad"
#])

#with tab1:
    #render_tab_calendario(periodo_global, casa_global),render_tab_inclusiones()

#with tab2:
    #render_tab_reservas()

#with tab3:
    #render_tab_facturacion()

#with tab4:
   # render_tab_auditoria()

#with tab5:
   # render_tab_configuracion()

#with tab6:
    #render_tab_contabilidad()
