import pdfkit
from datetime import datetime
import streamlit as st
import platform
import os

# --- 1. CONFIGURACIÓN ÚNICA DE PDFKIT ---
def obtener_configuracion():
    if platform.system() == "Windows":
        ruta = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        if os.path.exists(ruta):
            return pdfkit.configuration(wkhtmltopdf=ruta)
        else:
            # Si no existe, intentamos la ruta de 32 bits por si acaso
            ruta_x86 = r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
            if os.path.exists(ruta_x86):
                return pdfkit.configuration(wkhtmltopdf=ruta_x86)
    return pdfkit.configuration()

# Definimos config UNA SOLA VEZ
config_pdf = obtener_configuracion()

# --- 2. FUNCIONES DE APOYO ---
def formato_moneda(valor):
    """Muestra precios con formato $1,234.56"""
    return f"${valor:,.2f}"

def generar_pdf_factura(datos_reserva, desglose_pago):
    """
    Función unificada para generar el comprobante.
    datos_reserva: dict con {'cliente', 'villa', 'f_in', 'f_out'}
    desglose_pago: dict con {'sub_estancia', 'sub_extras', 'iva', 'total'}
    """
    fecha_emision = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; color: #333; padding: 20px; }}
            .header {{ text-align: center; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .tabla {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            .tabla th, .tabla td {{ border: 1px solid #eee; padding: 10px; text-align: left; }}
            .tabla th {{ background-color: #f8f9fa; }}
            .total {{ text-align: right; font-weight: bold; font-size: 1.3em; margin-top: 30px; color: #1f77b4; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>HOSTAL ALEGRÍA</h1>
            <p>Comprobante de Pago - Calinout Pro</p>
        </div>
        
        <div style="margin-top: 20px;">
            <p><strong>Cliente:</strong> {datos_reserva.get('cliente', 'N/A')}</p>
            <p><strong>Villa/Habitación:</strong> {datos_reserva.get('villa', 'N/A')}</p>
            <p><strong>Periodo:</strong> {datos_reserva.get('f_in', '')} al {datos_reserva.get('f_out', '')}</p>
            <p><strong>Fecha de Emisión:</strong> {fecha_emision}</p>
        </div>

        <table class="tabla">
            <thead>
                <tr>
                    <th>Descripción del Concepto</th>
                    <th style="text-align: right;">Monto</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Estadía en Propiedad</td>
                    <td style="text-align: right;">{formato_moneda(desglose_pago.get('sub_estancia', 0))}</td>
                </tr>
                <tr>
                    <td>Servicios Adicionales / Extras</td>
                    <td style="text-align: right;">{formato_moneda(desglose_pago.get('sub_extras', 0))}</td>
                </tr>
                <tr>
                    <td>Impuesto sobre Venta (IVA 15%)</td>
                    <td style="text-align: right;">{formato_moneda(desglose_pago.get('sub_iva', desglose_pago.get('iva', 0)))}</td>
                </tr>
            </tbody>
        </table>

        <div class="total">
            TOTAL NETO A PAGAR: {formato_moneda(desglose_pago.get('total', 0))}
        </div>
        
        <div style="margin-top: 50px; font-size: 0.8em; text-align: center; color: #888;">
            Gracias por su preferencia. Este documento sirve como comprobante de pago.
        </div>
    </body>
    </html>
    """
    
    try:
        # Usamos config_pdf que definimos arriba
        return pdfkit.from_string(html, False, configuration=config_pdf)
    except Exception as e:
        st.error(f"No se pudo generar el PDF. Verifica que wkhtmltopdf esté instalado. Error: {e}")
        return None