import mysql.connector
import streamlit as st

def obtener_conexion():
    """Conexión limpia usando los secretos de Streamlit Cloud."""
    try:
        conexion = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=st.secrets["mysql"]["port"],
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            autocommit=True
        )
        return conexion
    except mysql.connector.Error as err:
        st.error(f"Error de conexión: {err}")
        return None

def ejecutar_query(query, params=(), fetch=False):
    """Ejecuta SQL de forma segura."""
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            return cursor.fetchall() if fetch else True
        except mysql.connector.Error as e:
            st.error(f"Error en query: {e}")
        finally:
            conn.close()
    return None
    
