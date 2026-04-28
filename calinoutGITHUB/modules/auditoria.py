import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime, timedelta
import time
import io

def render_tab_auditoria():
    st.header("📊 Reporte Detallado de Operaciones")
    st.markdown("Consulta el historial de huéspedes, ingresos y gestiona correcciones de facturación.")

    # --- 1. FILTROS DE FECHA Y AGRUPACIÓN ---
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        tipo_reporte = st.selectbox("Agrupar resumen por:", ["Día", "Semana", "Mes", "Habitación"])
    with col_f2:
        fecha_inicio = st.date_input("Desde:", datetime.now() - timedelta(days=30))
    with col_f3:
        fecha_fin = st.date_input("Hasta:", datetime.now())

    try:
        conn = get_connection()
        # buffered=True para evitar errores de resultados no leídos
        cursor = conn.cursor(dictionary=True, buffered=True)

        # --- 2. LÓGICA DE RESUMEN EJECUTIVO (Gráficos y Métricas) ---
        if tipo_reporte == "Día":
            sql_res = "SELECT fecha_entrada AS Periodo, COUNT(*) AS Reservas, SUM(precio_noche + extras_total) AS Total FROM reservas WHERE fecha_entrada BETWEEN %s AND %s GROUP BY fecha_entrada ORDER BY fecha_entrada DESC"
        elif tipo_reporte == "Semana":
            sql_res = "SELECT YEARWEEK(fecha_entrada) AS Periodo, COUNT(*) AS Reservas, SUM(precio_noche + extras_total) AS Total FROM reservas WHERE fecha_entrada BETWEEN %s AND %s GROUP BY Periodo ORDER BY Periodo DESC"
        elif tipo_reporte == "Mes":
            sql_res = "SELECT DATE_FORMAT(fecha_entrada, '%Y-%m') AS Periodo, COUNT(*) AS Reservas, SUM(precio_noche + extras_total) AS Total FROM reservas WHERE fecha_entrada BETWEEN %s AND %s GROUP BY Periodo ORDER BY Periodo DESC"
        else:
            sql_res = "SELECT id_casa AS Habitación, COUNT(*) AS Reservas, SUM(precio_noche + extras_total) AS Total FROM reservas WHERE fecha_entrada BETWEEN %s AND %s GROUP BY id_casa ORDER BY Total DESC"

        cursor.execute(sql_res, (fecha_inicio, fecha_fin))
        resumen_data = cursor.fetchall()

        if resumen_data:
            df_resumen = pd.DataFrame(resumen_data)
            v_total = df_resumen['Total'].sum()
            r_total = df_resumen['Reservas'].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingresos Totales", f"${v_total:,.2f}")
            m2.metric("Noches Ocupadas", r_total)
            m3.metric("Promedio Reserva", f"${(v_total/r_total) if r_total > 0 else 0:,.2f}")
            st.bar_chart(df_resumen.set_index(df_resumen.columns[0])['Total'])

        st.divider()

        # --- 3. LOCALIZADOR INTELIGENTE Y REFACTURACIÓN ---
        st.subheader("🔍 Localizador y Gestión de Reservas")
        col_busq, col_filtro_pago = st.columns([3, 1])
        
        with col_busq:
            nombre_h = st.text_input("Buscar por nombre del huésped:", placeholder="Ej: Nestor", key="audit_search_name")
        with col_filtro_pago:
            # Valores exactos del ENUM en tu DB
            filtro_pago = st.selectbox("Estado de Pago:", ["Todos", "Pagado", "Pendiente", "Parcial"])

        query_b = "SELECT id_reserva, nombre_huesped, estado_pago, fecha_entrada FROM reservas WHERE 1=1"
        params_b = []

        if nombre_h:
            query_b += " AND nombre_huesped LIKE %s"
            params_b.append(f"%{nombre_h}%")
        if filtro_pago != "Todos":
            query_b += " AND estado_pago = %s"
            params_b.append(filtro_pago)

        query_b += " ORDER BY fecha_entrada DESC LIMIT 10"
        cursor.execute(query_b, params_b)
        res_busqueda = cursor.fetchall()

        if res_busqueda:
            opciones = [f"ID: {r['id_reserva']} | {r['nombre_huesped']} ({r['estado_pago']})" for r in res_busqueda]
            seleccion = st.selectbox("Seleccione una reserva para gestionar:", opciones, key="audit_select_res")
            
            id_sel = int(seleccion.split("ID: ")[1].split(" |")[0])
            estado_sel = seleccion.split("(")[1].replace(")", "")

            # Lógica de Reapertura: Solo si ya fue cobrada
            if estado_sel in ["Pagado", "Parcial"]:
                st.warning(f"La reserva #{id_sel} está marcada como {estado_sel}.")
                if st.button("🔓 Reabrir para Refacturación", type="primary", use_container_width=True):
                    cursor.execute("UPDATE reservas SET estado_pago = 'Pendiente' WHERE id_reserva = %s", (id_sel,))
                    conn.commit()
                    st.success(f"✅ Reserva #{id_sel} reabierta. Ahora aparecerá en Facturación.")
                    time.sleep(1)
                    st.rerun()
            else:
                st.info(f"La reserva #{id_sel} ya está Pendiente de cobro.")

        st.divider()

        # --- 4. BITÁCORA GENERAL CON FORMATO ---
        st.subheader("📋 Historial Completo")
        sql_det = """SELECT id_reserva AS ID, nombre_huesped AS 'Huésped', 
                            fecha_entrada AS 'Entrada', fecha_salida AS 'Salida',
                            (precio_noche + extras_total) AS 'Total', 
                            estado_pago AS 'Estado' 
                     FROM reservas WHERE fecha_entrada BETWEEN %s AND %s ORDER BY fecha_entrada DESC"""
        
        cursor.execute(sql_det, (fecha_inicio, fecha_fin))
        detalles_rows = cursor.fetchall()

        if detalles_rows:
            df_det = pd.DataFrame(detalles_rows)

            # Función para colores basada en el estado real
            def resaltar_pagos(val):
                if val == 'Pendiente': return 'background-color: #ff4b4b; color: white; font-weight: bold'
                if val == 'Pagado': return 'background-color: #28a745; color: white; font-weight: bold'
                return ''

            st.dataframe(
                df_det.style.map(resaltar_pagos, subset=['Estado'])
                            .format({"Total": "${:,.2f}"}),
                use_container_width=True, hide_index=True
            )

            # Exportación Excel (Opcional)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_det.to_excel(writer, index=False, sheet_name='Auditoria')
            st.download_button("📥 Descargar Excel", data=buffer.getvalue(), 
                               file_name="auditoria.xlsx", mime="application/vnd.ms-excel")

    except Exception as e:
        st.error(f"Error en Auditoría: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
