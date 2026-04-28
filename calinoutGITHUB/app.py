import streamlit as st
import sys
import os
from datetime import date, timedelta

# 1. Configuración de página (SIEMPRE PRIMERO)
st.set_page_config(page_title="Calinout Pro", layout="wide")

# 2. Configuración de rutas
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.append(root_path)

# 3. Importaciones
from database import get_connection

try:
    from modules.calendario import render_tab_calendario, render_tab_inclusiones
    from modules.reservas import render_tab_reservas
    from modules.facturacion import render_tab_facturacion
    from modules.auditoria import render_tab_auditoria
    from modules.configuracion import render_tab_configuracion
    from modules.contabilidad import render_tab_contabilidad
except ImportError as e:
    st.error(f"⚠️ Error cargando módulos: {e}")

# --- GESTIÓN DE SESIÓN REAL ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario_nombre = None

# Función para validar contra TiDB
def validar_usuario(user, pw):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT nombre_completo, rol FROM usuarios WHERE usuario = %s AND password = %s AND activo = 1"
        cursor.execute(query, (user, pw))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return resultado
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("🏨 Calinout Pro - Acceso al Sistema")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                user_data = validar_usuario(u, p)
                if user_data:
                    st.session_state.autenticado = True
                    st.session_state.rol = user_data['rol']
                    st.session_state.usuario_nombre = user_data['nombre_completo']
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    st.stop()

# --- DATOS PARA LA APP ---
def obtener_nombres_villas():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nombre_personalizado FROM nombres_casas WHERE activo = 1")
        villas = [row['nombre_personalizado'] for row in cursor.fetchall()]
        conn.close()
        return villas if villas else ["Villa 1"]
    except:
        return ["Cargando..."]

lista_villas = obtener_nombres_villas()
hoy = date.today()

# --- SIDEBAR MEJORADO ---
with st.sidebar:
    st.title("🏨 Calinout Pro")
    
    # Aquí movemos la info del usuario al Subheader como pediste
    st.subheader(f"👤 {st.session_state.usuario_nombre}")
    st.caption(f"Rol: {st.session_state.rol.upper()}")
    
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()
    
    st.divider()
    
    # Filtros Globales
    casa_global = st.multiselect("Filtrar por Casa", options=lista_villas)
    periodo_global = st.date_input("Rango", value=[hoy, hoy + timedelta(days=7)])
    
    st.divider()
    
    # Gestión de Estado (Bloqueos)
    st.subheader("🛠️ Gestión de Estado")
    with st.expander("Bloquear/Desbloquear"):
        with st.form("form_bloqueo"):
            v_bloqueo = st.selectbox("Unidad", lista_villas)
            nuevo_estado = st.selectbox("Estado", ["Libre", "Bloqueado", "Mantenimiento"])
            if st.form_submit_button("Actualizar"):
                # Aquí iría tu lógica de UPDATE en TiDB
                st.success("Estado actualizado")

# --- RENDERIZADO POR ROLES ---
rol = st.session_state.rol

if rol == "admin":
    tabs = st.tabs(["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📊 Auditoría", "📋 Inclusiones", "💰 Contabilidad", "⚙️ Configuración"])
    with tabs[0]: render_tab_calendario(periodo_global, casa_global)
    with tabs[1]: render_tab_reservas()
    with tabs[2]: render_tab_facturacion()
    with tabs[3]: render_tab_auditoria()
    with tabs[4]: render_tab_inclusiones()
    with tabs[5]: render_tab_contabilidad()
    with tabs[6]: render_tab_configuracion()

elif rol == "contador":
    tabs = st.tabs(["🧾 Facturación", "📊 Auditoría", "💰 Contabilidad"])
    with tabs[0]: render_tab_facturacion()
    with tabs[1]: render_tab_auditoria()
    with tabs[2]: render_tab_contabilidad()

elif rol == "agente": # El rol de tu colega recepcionista
    tabs = st.tabs(["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📋 Inclusiones"])
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
