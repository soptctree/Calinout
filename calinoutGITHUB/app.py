import streamlit as st
import sys
import os
from datetime import date, timedelta

# Configuración de rutas
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.append(root_path)

# Importaciones limpias
from database import get_connection

try:
    from modules.calendario import render_tab_calendario, render_tab_inclusiones
    from modules.reservas import render_tab_reservas
    from modules.facturacion import render_tab_facturacion
    from modules.auditoria import render_tab_auditoria
    from modules.configuracion import render_tab_configuracion, seccion_admin_costos
    from modules.contabilidad import render_tab_contabilidad
except ImportError as e:
    st.error(f"Error cargando módulos: {e}")

# ... Aquí sigue el resto de tu código (título, pestañas, etc.) ...

if "factura_generada" not in st.session_state:
        st.session_state.factura_generada = False

# Importación de tus módulos
from modules.calendario import render_tab_calendario, render_tab_inclusiones
from modules.reservas import render_tab_reservas
from modules.facturacion import render_tab_facturacion
from modules.auditoria import render_tab_auditoria
from modules.configuracion import render_tab_configuracion
from modules.contabilidad import render_tab_contabilidad
from modules.configuracion import render_tab_configuracion, seccion_admin_costos

st.set_page_config(page_title="Calinout Pro", layout="wide")



# --- LÓGICA PARA OBTENER TODAS LAS CASAS ---
def obtener_nombres_villas():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nombre_personalizado FROM nombres_casas WHERE activo = 1")
        villas = [row['nombre_personalizado'] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return villas
    except Exception as e:
        st.error(f"Error cargando villas: {e}")
        return ["Villa Ometepe", "Cabaña Maderas"]

lista_villas = obtener_nombres_villas()
hoy = date.today()

# --- TODO ESTO VA DENTRO DEL SIDEBAR ---
#######XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX####################
# --- SIMULACIÓN DE LOGIN EN EL SIDEBAR ---
st.sidebar.title("🔐 Control de Acceso")
usuario_simulado = st.sidebar.selectbox(
    "Iniciar sesión como:",
    ["Recepcionista (Limitado)", "Contador (Finanzas)", "Admin (Acceso Total)"]
)

# Definir el rol en el session_state para que otros módulos lo lean
if "Admin" in usuario_simulado:
    st.session_state.rol = "admin"
elif "Contador" in usuario_simulado:
    st.session_state.rol = "contador"
else:
    st.session_state.rol = "recepcionista"

st.sidebar.info(f"Usuario activo: {usuario_simulado}")
######XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#############
# --- TODO ESTO VA DENTRO DEL SIDEBAR ---
with st.sidebar:
    st.title("🏨 Calinout Pro")
    
    # 1. FILTRO ÚNICO (Aquí estaba el error, ahora solo hay uno)
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
    
    # 2. GESTIÓN DE ESTADO
    st.subheader("🛠️ Gestión de Estado")
    with st.expander("Bloquear/Desbloquear"):
        with st.form("form_bloqueo_sidebar", clear_on_submit=True):
            v_bloqueo = st.selectbox("Unidad", lista_villas)
            f_bloqueo = st.date_input("Fecha", value=hoy)
            nuevo_estado = st.selectbox("Nuevo Estado", ["Libre", "Bloqueado", "Mantenimiento"])
            submit_bloqueo = st.form_submit_button("Actualizar", key="btn_update_status")

        if submit_bloqueo:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # SQL con INSERT ... ON DUPLICATE KEY UPDATE
                # Tenemos 4 marcadores %s, por lo tanto necesitamos 4 valores en la tupla
                sql_update = """
                    INSERT INTO ocupacion (id_casa, fecha, estado)
                    VALUES ((SELECT id_casa FROM nombres_casas WHERE nombre_personalizado = %s), %s, %s)
                    ON DUPLICATE KEY UPDATE estado = %s
                """
                
                # IMPORTANTE: Aquí pasamos exactamente 4 parámetros
                valores = (v_bloqueo, f_bloqueo, nuevo_estado, nuevo_estado)
                
                cursor.execute(sql_update, valores)
                conn.commit()
                
                st.success(f"✅ {v_bloqueo} actualizado a {nuevo_estado}")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al actualizar: {e}")
            finally:
                if conn:
                    cursor.close()
                    conn.close()

#########XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#############################




# --- DEFINICIÓN DINÁMICA DE PESTAÑAS SEGÚN EL ROL ---
if st.session_state.rol == "admin":
    # Agregamos "⚙️ Configuración" a la lista del Gerente
    nombres_tabs = ["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📊 Auditoría", "📋 Inclusiones", "💰 Contabilidad", "⚙️ Configuración"]
    tabs = st.tabs(nombres_tabs)
    
    with tabs[0]: render_tab_calendario(periodo_global, casa_global)
    with tabs[1]: render_tab_reservas()
    with tabs[2]: render_tab_facturacion()
    with tabs[3]: render_tab_auditoria()
    with tabs[4]: render_tab_inclusiones()
    with tabs[5]: render_tab_contabilidad()
    with tabs[6]: render_tab_configuracion() # <--- Aquí recuperas el módulo

elif st.session_state.rol == "contador":
    nombres_tabs = ["🧾 Facturación", "📊 Auditoría", "💰 Contabilidad"]
    tabs = st.tabs(nombres_tabs)
    with tabs[0]: render_tab_facturacion()
    with tabs[1]: render_tab_auditoria()
    with tabs[2]: render_tab_contabilidad()

else: # Recepcionista
    # Para el recepcionista, el calendario y las inclusiones son lo más importante
    nombres_tabs = ["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📋 Inclusiones"]
    tabs = st.tabs(nombres_tabs)
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
