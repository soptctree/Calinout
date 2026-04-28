import mysql.connector
import streamlit as st

def get_connection():
    """Establece la conexión con la base de datos MySQL."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="ocupacion_calinout"
        )
        return conn
    except mysql.connector.Error as e:
        st.error(f"Error al conectar a la base de datos: {e}")
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