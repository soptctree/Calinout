import streamlit as st
import sys
import os
from datetime import date, timedelta

# 1. Configuración de página (DEBE SER LO PRIMERO)
st.set_page_config(page_title="Calinout Pro", layout="wide")

# 2. Configuración de rutas e importaciones
from database import get_connection
try:
    from database import get_connection
try:
    from modules.calendario import render_tab_calendar, render_tab_inclusiones
    from modules.reservas import render_tab_reservas
    from modules.facturacion import render_tab_facturacion
    from modules.auditoria import render_tab_auditoria
    from modules.configuracion import render_tab_configuracion
    from modules.contabilidad import render_tab_contabilidad
except ImportError as e:
    st.error(f"⚠️ Error cargando módulos: {e}")

# --- GESTIÓN DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario_nombre = None

def validar_usuario(user, pw):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Solo permite usuarios activos (activo = 1)
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
    st.title("🏨 Calinout Pro - Acceso")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                user_data = validar_usuario(u, p)
                if user_data:
                    st.session_state.autenticado = True
                    st.session_state.rol = user_data['rol']
                    st.session_state.usuario_nombre = user_data['nombre_completo']
                    st.rerun()
                else:
                    st.error("Acceso denegado: Credenciales incorrectas o usuario bloqueado.")
    st.stop()

# --- LÓGICA DE GESTIÓN DE USUARIOS (Funciones de DB) ---
def agregar_usuario_db(nombre, user, pas, rol_asignado):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO usuarios (nombre_completo, usuario, password, rol, activo) VALUES (%s, %s, %s, %s, 1)"
        cursor.execute(query, (nombre, user, pas, rol_asignado))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error al crear: {e}")
        return False

def cambiar_estado_usuario(user, estado):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "UPDATE usuarios SET activo = %s WHERE usuario = %s"
        cursor.execute(query, (estado, user))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏨 Calinout Pro")
    # Subheader con info del usuario real
    st.subheader(f"👤 {st.session_state.usuario_nombre}")
    st.caption(f"Perfil: {st.session_state.rol.upper()}")
    
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    
    st.divider()
    periodo_global = st.date_input("Periodo", value=[date.today(), date.today() + timedelta(days=7)])

# --- CORRECCIÓN CLAVE: Definir 'rol' antes de los IF ---
rol = st.session_state.rol 

# --- PESTAÑAS POR ROL ---
if rol == "admin":
    nombres_tabs = ["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📊 Auditoría", "📋 Inclusiones", "💰 Contabilidad", "⚙️ Configuración"]
    tabs = st.tabs(nombres_tabs)
    
    with tabs[0]: render_tab_calendario(periodo_global, [])
    with tabs[1]: render_tab_reservas()
    with tabs[2]: render_tab_facturacion()
    with tabs[3]: render_tab_auditoria()
    with tabs[4]: render_tab_inclusiones()
    with tabs[5]: render_tab_contabilidad()
    with tabs[6]:
        render_tab_configuracion()
        
        # --- CONSOLA DE GESTIÓN DE USUARIOS (Sincronizada con DB) ---
        st.divider()
        st.header("👥 Gestión de Usuarios y Accesos")
        
        # 1. Visualización
        st.subheader("Usuarios Registrados en el Sistema")
        try:
            import pandas as pd
            conn = get_connection()
            df_usuarios = pd.read_sql("SELECT nombre_completo, usuario, rol, activo FROM usuarios", conn)
            conn.close()
            st.dataframe(df_usuarios, use_container_width=True)
        except Exception as e:
            st.error(f"Error al cargar lista: {e}")
            df_usuarios = pd.DataFrame()

        # 2. Acciones
        col_new, col_status = st.columns(2)
        with col_new:
            st.subheader("➕ Registrar Nuevo")
            with st.form("form_new_user", clear_on_submit=True):
                n_nom = st.text_input("Nombre Completo")
                n_usr = st.text_input("ID Usuario")
                n_pwd = st.text_input("Pass", type="password")
                n_r = st.selectbox("Rol", ["admin", "agente", "contador"])
                if st.form_submit_button("Guardar"):
                    if agregar_usuario_db(n_nom, n_usr, n_pwd, n_r):
                        st.success("Usuario creado")
                        st.rerun()

        with col_status:
            st.subheader("🚫 Bloquear / ✅ Activar")
            if not df_usuarios.empty:
                u_sel = st.selectbox("Seleccionar Usuario", df_usuarios['usuario'].tolist())
                # Lógica de botones para Activar/Desactivar
                c1, c2 = st.columns(2)
                if c1.button("🚫 Bloquear"):
                    cambiar_estado_usuario(u_sel, 0)
                    st.rerun()
                if c2.button("✅ Activar"):
                    cambiar_estado_usuario(u_sel, 1)
                    st.rerun()

elif rol == "contador":
    tabs = st.tabs(["🧾 Facturación", "📊 Auditoría", "💰 Contabilidad"])
    with tabs[0]: render_tab_facturacion()
    with tabs[1]: render_tab_auditoria()
    with tabs[2]: render_tab_contabilidad()

else: # agente
    tabs = st.tabs(["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📋 Inclusiones"])
    with tabs[0]: render_tab_calendario(periodo_global, [])
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
