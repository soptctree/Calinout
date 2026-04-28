import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime, timedelta
import plotly.express as px # Opcional, si no lo tienes usa st.bar_chart

def calcular_costo_operativo(id_casa, noches, personas):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscamos la ficha técnica de la unidad
        cursor.execute("SELECT * FROM ficha_tecnica_costos WHERE id_casa = %s", (id_casa,))
        ficha = cursor.fetchone()
        
        if ficha:
            # Fórmula: Limpieza + (Amenities * Personas) + (Energía * Noches)
            total_costo = float(
                ficha['costo_limpieza_fijo'] + 
                (ficha['costo_amenities_pax'] * personas) + 
                (ficha['costo_energia_noche'] * noches)
            )
            return total_costo
        return 0.0 # Si no hay ficha configurada
    except Exception as e:
        print(f"Error calculando costos: {e}")
        return 0.0
    finally:
        conn.close()

def render_tab_contabilidad():
    st.header("🏢 Centro de Inteligencia Contable")
    st.markdown("Analiza el rendimiento de Calinout Pro con desgloses detallados de ingresos.")

    # --- 1. CONFIGURACIÓN DE FILTROS ---
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        agrupacion = st.selectbox("Vista temporal:", ["Día", "Mes", "Año"])
    with col_t2:
        # Rango amplio por defecto para ver comparativas
        rango = st.date_input("Periodo de análisis:", [datetime.now() - timedelta(days=180), datetime.now()])

    if len(rango) == 2:
        f_inicio, f_fin = rango
        
        # Definir el formato de fecha según la agrupación
        if agrupacion == "Día": format_sql = "%Y-%m-%d"
        elif agrupacion == "Mes": format_sql = "%Y-%m"
        else: format_sql = "%Y"

        # --- 2. SQL MAESTRO DE DESGLOSE ---
        # Basado en tu estructura: precio_noche, extras_total, adultos, ninos, mascotas
        sql = f"""
            SELECT 
                DATE_FORMAT(fecha_entrada, '{format_sql}') AS Periodo,
                COUNT(id_reserva) AS Total_Reservas,
                SUM(precio_noche * DATEDIFF(fecha_salida, fecha_entrada)) AS Hospedaje_Puro,
                SUM(extras_total) AS Total_Extras,
                SUM(ninos) AS Cantidad_Niños,
                SUM(mascotas) AS Cantidad_Mascotas,
                SUM((precio_noche + extras_total) * (impuestos_porcentaje/100)) AS IVA_Total,
                SUM(precio_noche + extras_total) AS Venta_Neta
            FROM reservas
            WHERE fecha_entrada BETWEEN %s AND %s AND estado_pago = 'Pagado'
            GROUP BY Periodo
            ORDER BY Periodo ASC
        """

        try:
            conn = get_connection()
            df = pd.read_sql(sql, conn, params=(f_inicio, f_fin))
            conn.close()

            if not df.empty:
                # --- 3. DASHBOARD DE MÉTRICAS ---
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Ingreso Neto", f"${df['Venta_Neta'].sum():,.2f}")
                m2.metric("Extras Vendidos", f"${df['Total_Extras'].sum():,.2f}")
                m3.metric("IVA a Declarar", f"${df['IVA_Total'].sum():,.2f}")
                m4.metric("Reservas", df['Total_Reservas'].sum())

                # --- 4. GRÁFICOS COMPARATIVOS ---
                st.subheader("📊 Comparativa de Ventas")
                
                # Gráfico de áreas para ver la tendencia de Hospedaje vs Extras
                st.area_chart(df.set_index('Periodo')[['Hospedaje_Puro', 'Total_Extras']])

                # --- 5. TABLA DE DETALLE CONTABLE ---
                st.subheader("📑 Libro de Ventas Detallado")
                st.dataframe(
                    df.style.format({
                        "Hospedaje_Puro": "${:,.2f}",
                        "Total_Extras": "${:,.2f}",
                        "IVA_Total": "${:,.2f}",
                        "Venta_Neta": "${:,.2f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
                st.caption("Nota: Este reporte solo incluye reservas con estado 'Pagado' para fines contables.")

            else:
                st.info("No hay datos pagados en este rango para mostrar el desglose.")
        
        except Exception as e:
            st.error(f"Error al generar reporte: {e}")