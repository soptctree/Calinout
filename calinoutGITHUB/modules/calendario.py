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

        # --- EXPORTACIÓN A EXCEL ---
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
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Error al generar inclusiones: {e}")

def render_tab_calendario(periodo, casas_seleccionadas):
    if not periodo or len(periodo) < 2:
        st.info("📅 Por favor, selecciona un rango de fechas (Inicio y Fin) en el panel lateral.")
        return 
    
    fecha_inicio, fecha_fin = periodo

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query_casas = "SELECT id_casa, nombre_personalizado FROM nombres_casas WHERE activo = 1"
        if casas_seleccionadas:
            formato_casas = "', '".join(casas_seleccionadas)
            query_casas += f" AND nombre_personalizado IN ('{formato_casas}')"
        
        cursor.execute(query_casas)
        rows_casas = cursor.fetchall()
        nombres_villas = [r['nombre_personalizado'] for r in rows_casas]

        rango_dias = pd.date_range(start=fecha_inicio, end=fecha_fin)
        columnas_fechas = [d.strftime('%a %d/%m') for d in rango_dias]
        mapeo_fechas = {d.strftime('%a %d/%m'): d.date() for d in rango_dias}

        df_display = pd.DataFrame("🟢 Libre", index=nombres_villas, columns=columnas_fechas)

        query_bloqueos = """
            SELECT n.nombre_personalizado, o.fecha, o.estado 
            FROM ocupacion o
            JOIN nombres_casas n ON o.id_casa = n.id_casa
            WHERE o.fecha BETWEEN %s AND %s
        """
        cursor.execute(query_bloqueos, (fecha_inicio, fecha_fin))
        for b in cursor.fetchall():
            casa, f_str = b['nombre_personalizado'], b['fecha'].strftime('%a %d/%m')
            if casa in df_display.index and f_str in df_display.columns:
                df_display.at[casa, f_str] = "🔒 BLOQUEADO" if b['estado'] == "Bloqueado" else "🛠️ MANT"

        # Lógica de Reservas Corregida para evitar falsos positivos
        query_reservas = """
            SELECT r.nombre_huesped, n.nombre_personalizado, r.fecha_entrada, r.fecha_salida 
            FROM reservas r
            JOIN nombres_casas n ON r.id_casa = n.id_casa
            WHERE r.fecha_salida > %s AND r.fecha_entrada <= %s
        """
        cursor.execute(query_reservas, (fecha_inicio, fecha_fin))
        reservas = cursor.fetchall()

        for res in reservas:
            casa = res['nombre_personalizado']
            if casa in df_display.index:
                for col in columnas_fechas:
                    f_actual = mapeo_fechas[col]
                    nombre_corto = res['nombre_huesped'].split()[0]
                    
                    if f_actual == res['fecha_entrada']:
                        val_actual = df_display.at[casa, col]
                        df_display.at[casa, col] = f"🔄 Sal/Ent" if "🛫" in val_actual else f"🛬 {nombre_corto}"
                    
                    elif f_actual == res['fecha_salida']:
                        val_actual = df_display.at[casa, col]
                        df_display.at[casa, col] = f"🔄 Sal/Ent" if "🛬" in val_actual else f"🛫 {nombre_corto}"
                        
                    elif res['fecha_entrada'] < f_actual < res['fecha_salida']:
                        df_display.at[casa, col] = f"🔴 {nombre_corto}"

    except Exception as e:
        st.error(f"Error en calendario: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

    if not df_display.empty:
        def style_cells(val):
            if "🟢" in val: return 'background-color: #e8f5e9; color: #2e7d32;'
            if "🔴" in val: return 'background-color: #fff9c4; color: #b71c1c;' 
            if "🛬" in val: return 'background-color: #e3f2fd; color: #0d47a1; font-weight: bold;' 
            if "🛫" in val: return 'background-color: #fce4ec; color: #880e4f; font-weight: bold;' 
            if "🔄" in val: return 'background-color: #f3e5f5; color: #4a148c; border: 1px solid purple;' 
            if "🔒" in val or "🛠️" in val: return 'background-color: #eeeeee; color: #424242;'
            return ''

        st.dataframe(df_display.style.map(style_cells), use_container_width=True)
