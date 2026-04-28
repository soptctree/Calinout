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
        # Sumamos adultos y niños de los que llegan y los que ya están
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
            # Diccionario de hojas para iterar y corregir
            hojas = {
                'Llegadas': df_llegadas,
                'Huespedes_En_Casa': df_encasa,
                'Salidas': df_salidas,
                'Villas_Libres': df_libres
            }
            
            for nombre_hoja, df in hojas.items():
                df.to_excel(writer, sheet_name=nombre_hoja, index=False)
                # CORRECCIÓN DE CAPTURA: Ajustar ancho para evitar los "#######"
                worksheet = writer.sheets[nombre_hoja]
                for idx, col in enumerate(df.columns):
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
    # --- VALIDACIÓN DE SEGURIDAD ---
    if not periodo or len(periodo) == 0:
        st.info("📅 Por favor, selecciona un rango de fechas en el panel lateral para ver el calendario.")
        return # Detiene la ejecución de esta pestaña limpiamente
    
    if len(periodo) == 2:
        fecha_inicio, fecha_fin = periodo
    else:
        fecha_inicio = periodo[0]
        fecha_fin = fecha_inicio + timedelta(days=7)

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. OBTENER LAS CASAS ACTIVAS
        query_casas = "SELECT id_casa, nombre_personalizado FROM nombres_casas WHERE activo = 1"
        
        if casas_seleccionadas:
            formato_casas = "', '".join(casas_seleccionadas)
            query_casas += f" AND nombre_personalizado IN ('{formato_casas}')"
        
        cursor.execute(query_casas)
        rows_casas = cursor.fetchall()
        
        # Esto define los nombres para las filas del calendario
        nombres_villas = [r['nombre_personalizado'] for r in rows_casas]

        

        # 2. CREAR EL RANGO DE FECHAS
        rango_dias = pd.date_range(start=fecha_inicio, end=fecha_fin)
        columnas_fechas = [d.strftime('%a %d/%m') for d in rango_dias]
        mapeo_fechas = {d.strftime('%a %d/%m'): d.date() for d in rango_dias}

        # 3. INICIALIZAR EL DATAFRAME VACÍO
        df_display = pd.DataFrame("🟢 Libre", index=nombres_villas, columns=columnas_fechas)

        # 4. LEER BLOQUEOS (Tabla 'ocupacion') <-- ESTO ES LO QUE FALTA
        query_bloqueos = """
            SELECT n.nombre_personalizado, o.fecha, o.estado 
            FROM ocupacion o
            JOIN nombres_casas n ON o.id_casa = n.id_casa
            WHERE o.fecha BETWEEN %s AND %s
        """
        cursor.execute(query_bloqueos, (fecha_inicio, fecha_fin))
        bloqueos = cursor.fetchall()

        for b in bloqueos:
            casa = b['nombre_personalizado']
            f_str = b['fecha'].strftime('%a %d/%m')
            if casa in df_display.index and f_str in df_display.columns:
                if b['estado'] == "Bloqueado":
                    df_display.at[casa, f_str] = "🔒 BLOQUEADO"
                elif b['estado'] == "Mantenimiento":
                    df_display.at[casa, f_str] = "🛠️ MANTENIMIENTO"

        # 5. LEER RESERVAS (Tabla 'reservas') - Sobreescribe si hay huésped
        query_reservas = """
            SELECT r.nombre_huesped, n.nombre_personalizado, r.fecha_entrada, r.fecha_salida 
            FROM reservas r
            JOIN nombres_casas n ON r.id_casa = n.id_casa
            WHERE (r.fecha_entrada <= %s AND r.fecha_salida >= %s)
        """
        cursor.execute(query_reservas, (fecha_fin, fecha_inicio))
        reservas = cursor.fetchall()

        for res in reservas:
            casa = res['nombre_personalizado']
            if casa in df_display.index:
                for col in columnas_fechas:
                    f_actual = mapeo_fechas[col]
                    if f_actual == res['fecha_salida']:
                        df_display.at[casa, col] = f"🛫 {res['nombre_huesped'].split()[0]}"
                    elif res['fecha_entrada'] <= f_actual < res['fecha_salida']:
                        df_display.at[casa, col] = f"🔴 {res['nombre_huesped'].split()[0]}"
                    elif f_actual == res['fecha_entrada']:
                        df_display.at[casa, col] = f"🛬 {res['nombre_huesped'].split()[0]}"

    except Exception as e:
        st.error(f"Error en calendario: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

    # --- RENDERIZADO CON COLORES ---
    if not df_display.empty:
        def style_cells(val):
            if "🟢" in val: return 'background-color: #e8f5e9; color: #2e7d32;'
            if "🔴" in val: return 'background-color: #ffeeb2; color: #b71c1c;'
            if "🔒" in val: return 'background-color: #eeeeee; color: #424242; font-weight: bold;'
            if "🛠️" in val: return 'background-color: #fff3cd; color: #856404;'
            return ''

        st.dataframe(df_display.style.map(style_cells), use_container_width=True)
