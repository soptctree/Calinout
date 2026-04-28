import mysql.connector
import streamlit as st

def get_connection():
    try:
        # Streamlit reemplazará estas palabras por tus datos reales automáticamente
        conexion = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=int(st.secrets["mysql"]["port"]),
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            autocommit=True
        )
        return conexion
    except mysql.connector.Error as err:
        st.error(f"Error al conectar a la base de datos: {err}")
        return None

def ejecutar_query(query, params=(), fetch=False):
    """Función utilitaria para ejecutar SQL de forma segura."""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            return True
        except mysql.connector.Error as e:
            st.error(f"Error en la consulta: {e}")
        finally:
            conn.close()
    return None
