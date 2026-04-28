import mysql.connector
import streamlit as st

def get_connection():
    """Establece la conexión con la base de datos TiDB Cloud usando Secretos."""
    try:
        # Usamos st.secrets para conectar con la base de datos externa
        conexion = mysql.connector.connect(
            host=st.secrets["mysql"]["gateway01.us-east-1.prod.aws.tidbcloud.com"],
            port=st.secrets["mysql"]["4000"],
            user=st.secrets["mysql"]["656ozEuuzyBjeL5.root"],
            password=st.secrets["mysql"]["0VGZDnkyb6xY2xg8"],
            database=st.secrets["mysql"]["sys"]
        )
        return conexion
    except mysql.connector.Error as mi:
        st.error(f"Error al conectar a la base de datos: {mi}")
        return None
def ejecutar_query(query, params=(), fetch=False):
    """
    Función utilitaria para ejecutar SQL de forma segura.
    Si fetch=True, devuelve los resultados (SELECT).
    Si fetch=False, hace commit (INSERT, UPDATE, DELETE).
    """
    conn = get_connection()
    if conn:
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            cursor.execute(query, params)
            if fetch:
                resultado = cursor.fetchall()
                return resultado
            else:
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Error ejecutando query: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    return None
