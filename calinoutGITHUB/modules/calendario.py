import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime, timedelta
import io

def render_tab_inclusiones():
    st.header("📋 Reporte Operativo de Inclusiones")
    
    # LÓGICA DE AUDITORÍA NOCTURNA: Permitir seleccionar fecha (hoy o mañana)
    hoy_dt = datetime.now().date()
    fecha_reporte = st.date_input("📅 Generar reporte para el día:", hoy_dt)
    
    st.info(f"Mostrando previsión operativa para el: **{fecha_reporte.strftime('%d/%m/%Y')}**")

    try:
        conn = get_connection()
        
        # 1. LLEGADAS (Check-ins en la fecha seleccionada)
        query_llegadas = """
            SELECT r.nombre_huesped AS Huésped, n.nombre_personalizado AS Villa, 
                   r.adultos, r.ninos, r.mascotas, r.notas 
            FROM reservas r
            JOIN nombres_casas n ON r.id_casa = n.id_casa
            WHERE r.fecha_entrada = %s
        """
        df_llegadas = pd.read_sql(query_llegadas, conn, params=(fecha_reporte,))

        # 2. EN CASA (Stay-overs: Huespedes que ya están y no salen hoy)
        query_encasa = """
            SELECT r.nombre_huesped AS Huésped, n.nombre_personalizado AS Villa, 
                   r.fecha_salida AS Sale_el, r.adultos, r.ninos
            FROM reservas r
            JOIN nombres_casas n ON r.id_casa = n.id_casa
            WHERE %s > r.fecha_entrada AND %s < r.fecha_salida
        """
        df_encasa = pd.read_sql(query_encasa, conn, params=(fecha_reporte, fecha_reporte))

        # 3. SALIDAS (Check-outs hoy)
        query_salidas = """
            SELECT r.nombre_huesped AS Huésped, n.nombre_personalizado AS Villa, 
                   r.estado_pago
            FROM reservas r
            JOIN nombres_casas n ON r.id_casa = n.id_casa
            WHERE r.fecha_salida = %s
        """
        df_salidas = pd.read_sql(query_salidas, conn, params=(fecha_reporte,))

        # 4. DISPONIBLES
        query_libres = """
            SELECT nombre_personalizado AS Villa FROM nombres_casas 
            WHERE activo = 1 AND id_casa NOT IN (
                SELECT id_casa FROM reservas WHERE %s >= fecha_entrada AND %s < fecha_salida
            )
        """
        df_libres = pd.read_sql(query_libres, conn, params=(fecha_reporte, fecha_reporte))
        conn.close()

        # --- CÁLCULO DE RESUMEN PARA COCINA (PAX TOTAL) ---
        tot_adultos = df_llegadas['adultos'].sum() + df_encasa['adultos'].sum()
        tot_ninos = df_llegadas['ninos'].sum() + df_encasa['ninos'].sum()
        pax_total = tot_adultos + tot_ninos

        # Mostrar cuadro de resumen destacado
        st.success(f"☕ **Resumen para Alimentos y Bebidas:** El hotel abre con **{pax_total} Pax** ({tot_adultos} Adultos y {tot_ninos} Niños).")

        # --- DISEÑO DE PANTALLA ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(f"🛬 Llegadas ({len(df_llegadas)})")
            st.dataframe(df_llegadas[['Huésped', 'Villa']], use_container_width=True, hide_index=True)
        with col2:
            st.subheader(f"🏠 En Casa ({len(df_encasa)})")
            st.dataframe(df_encasa[['Huésped', 'Villa']], use_container_width=True, hide_index=True)
        with col3:
            st.subheader(f"🛫 Salidas ({len(df_salidas)})")
            st.dataframe(df_salidas[['Huésped', 'Villa']], use_container_width=True, hide_index=True)

        st.divider()

        # --- EXPORTACIÓN A EXCEL CON CORRECCIÓN DE COLUMNAS ---
        st.subheader("📥 Descargar Reporte para Áreas")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            hojas = {
                'Llegadas': df_llegadas,
                'Huespedes_En_Casa': df_encasa,
                'Salidas': df_salidas,
                'Villas_Libres': df_libres
            }
            
            for nombre_hoja, df in hojas.items():
                df.to_excel(writer, sheet_name=nombre_hoja, index=False)
                worksheet = writer.sheets[nombre_hoja]
                for idx, col in enumerate(df.columns):
                    if not df[col].empty:
                        max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(idx, idx, max_len)

        st.download_button(
            label="📗 Descargar Reporte Operativo (XLSX)",
            data=output.getvalue(),
            file_name=f"Reporte_Operativo_{fecha_reporte}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
