import streamlit as st
import sys
import os
from datetime import date, timedelta

# 1. Configuración de página
st.set_page_config(page_title="Calinout Pro", layout="wide")

# 2. Configuración de rutas e importaciones
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

# --- GESTIÓN DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario_nombre = None

def validar_usuario(user, pw):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # EL BLOQUEO FUNCIONA AQUÍ: Solo entra si activo = 1
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

# --- LÓGICA DE GESTIÓN DE USUARIOS (Solo para Admin) ---
def agregar_usuario_db(nombre, user, pas, rol):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO usuarios (nombre_completo, usuario, password, rol, activo) VALUES (%s, %s, %s, %s, 1)"
        cursor.execute(query, (nombre, user, pas, rol))
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
    st.subheader(f"👤 {st.session_state.usuario_nombre}")
    st.caption(f"Perfil: {st.session_state.rol.upper()}")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    st.divider()
    # Filtros temporales (mantener los que ya tenías)
    periodo_global = st.date_input("Periodo", value=[date.today(), date.today() + timedelta(days=7)])

# --- PESTAÑAS POR ROL ---
# --- DENTRO DE LA PESTAÑA DE CONFIGURACIÓN (Solo para Admin) ---
if rol == "admin":
    st.divider()
    st.header("👥 Gestión de Usuarios y Accesos")

    # 1. VISUALIZACIÓN DE USUARIOS ACTUALES
    st.subheader("Usuarios Registrados en el Sistema")
    try:
        conn = get_connection()
        # Traemos la lista actualizada de la base de datos
        query_lista = "SELECT nombre_completo, usuario, rol, activo FROM usuarios"
        import pandas as pd
        df_usuarios = pd.read_sql(query_lista, conn)
        conn.close()

        # Mostramos la tabla con un formato limpio
        st.dataframe(
            df_usuarios.style.map(
                lambda x: 'color: red;' if x == 0 else ('color: green;' if x == 1 else ''), 
                subset=['activo']
            ),
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Error al cargar la lista: {e}")

    # 2. ACCIONES DE GESTIÓN
    col_new, col_status = st.columns(2)
    
    with col_new:
        st.subheader("➕ Registrar Nuevo")
        with st.form("form_new_user", clear_on_submit=True):
            n_nom = st.text_input("Nombre Completo")
            n_usr = st.text_input("ID de Usuario (Login)")
            n_pwd = st.text_input("Contraseña Inicial", type="password")
            n_rol = st.selectbox("Asignar Rol", ["admin", "agente", "contador"])
            if st.form_submit_button("Guardar en Base de Datos"):
                if agregar_usuario_db(n_nom, n_usr, n_pwd, n_rol):
                    st.success(f"Usuario {n_usr} creado. ¡Ya puede iniciar sesión!")
                    st.rerun() # Recargamos para que aparezca en la tabla de arriba

    with col_status:
        st.subheader("🚫 Bloquear / ✅ Activar")
        # Aquí usamos la lista de usuarios del DataFrame para el selector
        if not df_usuarios.empty:
            usuario_a_modificar = st.selectbox(
                "Seleccione el usuario a modificar", 
                options=df_usuarios['usuario'].tolist()
            )
            
            # Verificamos el estado actual para mostrar el botón correcto
            estado_actual = df_usuarios[df_usuarios['usuario'] == usuario_a_modificar]['activo'].values[0]
            
            if estado_actual == 1:
                if st.button("🚫 Bloquear Acceso", use_container_width=True, type="primary"):
                    if cambiar_estado_usuario(usuario_a_modificar, 0):
                        st.warning(f"Usuario {usuario_a_modificar} bloqueado.")
                        st.rerun()
            else:
                if st.button("✅ Activar Acceso", use_container_width=True):
                    if cambiar_estado_usuario(usuario_a_modificar, 1):
                        st.success(f"Usuario {usuario_a_modificar} activado.")
                        st.rerun()

elif rol == "contador":
    tabs = st.tabs(["🧾 Facturación", "📊 Auditoría", "💰 Contabilidad"])
    # ... renderizados de contador ...
else: # agente
    tabs = st.tabs(["📅 Calendario", "📝 Reservas", "🧾 Facturación", "📋 Inclusiones"])
    # ... renderizados de agente ...
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
