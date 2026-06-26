import os
import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
import re

# ------------------------------------------------------------
# IMPORTACIÓN ROBUSTA DE SQUARE (compatible con versiones 35.x y 44.x)
# ------------------------------------------------------------
try:
    from square.client import Client  # Versión 35.x
except ImportError:
    import square
    Client = square.Client  # Versión 44.x (fallback)

# ------------------------------------------------------------
# IMPORTAR MOTOR DE KPIS
# ------------------------------------------------------------
try:
    from motor_kpis import procesar_periodo, validar_esquema_datos, BENCHMARK_SECTORES
except ImportError:
    st.error("❌ No se encuentra 'motor_kpis.py'. Asegúrate de que el archivo está en la misma carpeta.")
    st.stop()

# ------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ------------------------------------------------------------
st.set_page_config(
    page_title="Retail Pulse - Analítica de Ventas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------
def convertir_fechas(df):
    if 'Fecha' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['Fecha']):
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    if not df.empty and 'Fecha' in df.columns:
        df['Dia_Semana'] = df['Fecha'].dt.day_name()
        df['Hora'] = df['Fecha'].dt.hour
        df['Dia_Num'] = df['Fecha'].dt.day
    return df

def limpiar_numero(valor):
    if isinstance(valor, (int, float)):
        return valor
    if isinstance(valor, str):
        valor = valor.replace('.', '').replace(',', '.')
        try:
            return float(valor)
        except:
            return 0.0
    return 0.0

# ------------------------------------------------------------
# ADAPTADOR DE SQUARE (CONEXIÓN SILENCIOSA)
# ------------------------------------------------------------
def obtener_token_square():
    """Obtiene el token de Square desde los secretos de Streamlit o variables de entorno."""
    try:
        token = st.secrets["SQUARE_ACCESS_TOKEN"]
        if token and token != "tu_token_aqui":
            return token
    except:
        pass
    
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if token and token != "tu_token_aqui":
        return token
    
    return None  # Silenciosamente

def obtener_datos_square(fecha_inicio, fecha_fin):
    """
    Obtiene órdenes de Square en el rango de fechas.
    Si falla, genera datos de demostración silenciosamente.
    """
    token = obtener_token_square()
    if not token:
        return generar_datos_demo(fecha_inicio, fecha_fin)
    
    try:
        client = Client(
            access_token=token,
            environment="sandbox"
        )
        
        start_str = fecha_inicio.strftime("%Y-%m-%dT00:00:00Z")
        end_str = fecha_fin.strftime("%Y-%m-%dT23:59:59Z")
        
        with st.spinner("🔄 Obteniendo datos de Square..."):
            result = client.orders.list_orders(
                location_id="main",
                begin_time=start_str,
                end_time=end_str,
                limit=200
            )
            
            orders = result.body.get('orders', [])
            
            if not orders:
                return generar_datos_demo(fecha_inicio, fecha_fin)
            
            datos = []
            for order in orders:
                fecha = pd.to_datetime(order.get('created_at'))
                total_money = order.get('total_money', {})
                amount = float(total_money.get('amount', 0)) / 100
                
                vendedor = "Vendedor_Default"
                if 'tenders' in order and order['tenders']:
                    for tender in order['tenders']:
                        if 'employee_id' in tender:
                            vendedor = tender['employee_id']
                            break
                
                unidades = 0
                for item in order.get('line_items', []):
                    unidades += int(item.get('quantity', 0))
                
                transacciones = 1
                horas_trabajadas = 1.0
                trafico_tienda = 50
                coste_hora = 12.50
                
                datos.append({
                    "Fecha": fecha,
                    "Vendedor_ID": vendedor,
                    "Ventas": amount,
                    "Transacciones": transacciones,
                    "Unidades": unidades,
                    "Horas_Trabajadas": horas_trabajadas,
                    "Trafico_Tienda": trafico_tienda,
                    "Coste_Hora": coste_hora
                })
            
            df = pd.DataFrame(datos)
            if df.empty:
                return generar_datos_demo(fecha_inicio, fecha_fin)
            
            return df, "Datos obtenidos correctamente desde Square"
            
    except Exception as e:
        # Silenciosamente usa datos de demostración
        return generar_datos_demo(fecha_inicio, fecha_fin)

def generar_datos_demo(fecha_inicio, fecha_fin):
    """
    Genera datos de demostración realistas.
    """
    vendedores = ["Vendedor_1 (Junior)", "Vendedor_2 (Senior)", "Vendedor_3 (Cajero)", "Vendedor_4 (Asesor)", "Vendedor_5 (Practicante)"]
    datos = []
    
    dias = (fecha_fin - fecha_inicio).days + 1
    np.random.seed(42)
    
    for dia in range(dias):
        fecha_base = datetime.combine(fecha_inicio + timedelta(days=dia), datetime.min.time())
        for hora in range(10, 21):
            dt = fecha_base.replace(hour=hora)
            num_vendedores = np.random.randint(2, 5)
            vendedores_turno = np.random.choice(vendedores, num_vendedores, replace=False)
            
            es_fin_semana = dt.weekday() >= 5
            es_pico = (hora >= 17 and hora <= 20) and es_fin_semana
            es_valle = (hora <= 13) and (dt.weekday() <= 2)
            
            if es_pico:
                trafico = np.random.randint(100, 160)
                conv_rate = np.random.uniform(0.25, 0.32)
            elif es_valle:
                trafico = np.random.randint(8, 20)
                conv_rate = np.random.uniform(0.40, 0.55)
            else:
                trafico = np.random.randint(30, 70)
                conv_rate = np.random.uniform(0.32, 0.42)
            
            trans_totales = max(1, int(trafico * conv_rate))
            trans_por_v = max(1, trans_totales // num_vendedores)
            
            for v in vendedores_turno:
                if "Asesor" in v:
                    aov_base = 48
                    u_base = 2.9
                elif "Senior" in v:
                    aov_base = 36
                    u_base = 2.2
                elif "Cajero" in v:
                    aov_base = 22
                    u_base = 1.2
                elif "Practicante" in v:
                    aov_base = 18
                    u_base = 1.1
                else:
                    aov_base = 20
                    u_base = 1.3
                
                trans = max(1, int(trans_por_v * np.random.uniform(0.7, 1.3)))
                ventas = round(trans * aov_base * np.random.uniform(0.9, 1.1), 2)
                unidades = max(trans, int(trans * u_base * np.random.uniform(0.9, 1.1)))
                
                datos.append({
                    "Fecha": dt,
                    "Vendedor_ID": v,
                    "Ventas": ventas,
                    "Transacciones": trans,
                    "Unidades": unidades,
                    "Horas_Trabajadas": round(1.0 / num_vendedores, 2),
                    "Trafico_Tienda": trafico,
                    "Coste_Hora": 12.50
                })
    
    df = pd.DataFrame(datos)
    return df, "Datos de demostración generados"

# ------------------------------------------------------------
# FUNCIÓN PARA GENERAR PDF (BÁSICO)
# ------------------------------------------------------------
def generar_pdf_simple(resultado, fecha_inicio, fecha_fin, cliente="Demo"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph("INFORME DE AUDITORÍA – RETAIL PULSE", styles['Title']))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Cliente: {cliente}", styles['Normal']))
        story.append(Paragraph(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.5*cm))
        
        kpi_data = [
            ["Métrica", "Valor"],
            ["Ventas Totales", f"{resultado.get('tot_ventas', '0')} €"],
            ["Transacciones", str(resultado.get('tot_trans', '0'))],
            ["VPH", f"{resultado.get('vph_global', '0')} €/h"],
            ["Conversión", f"{resultado.get('tasa_conv', '0')}%"],
            ["AOV", f"{resultado.get('aov_global', '0')} €"],
            ["UPT", str(resultado.get('upt_global', '0'))],
            ["Coste Laboral %", f"{resultado.get('coste_lab_pct', '0')}%"],
            ["Impacto Ineficiencia", f"{resultado.get('impacto_pct', '0')}%"]
        ]
        t = Table(kpi_data, colWidths=[5*cm, 5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (1,1), (1,-1), 'RIGHT'),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))
        
        vendedores = resultado.get('vendedores', [])
        if vendedores:
            story.append(Paragraph("Dictamen por Vendedor", styles['Heading2']))
            for v in vendedores[:3]:
                story.append(Paragraph(f"<b>{v['id']}</b> – {v['cuadrante']}", styles['Normal']))
                story.append(Paragraph(f"VPH: {v['vph']} €/h | AOV: {v['aov']} € | UPT: {v['upt']}", styles['Normal']))
                story.append(Paragraph(f"<b>Recomendación:</b> {v['recomendacion']}", styles['Normal']))
                story.append(Spacer(1, 0.3*cm))
        
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer
    except Exception as e:
        st.error(f"Error al generar PDF: {e}")
        return None

# ------------------------------------------------------------
# INTERFAZ PRINCIPAL DE STREAMLIT
# ------------------------------------------------------------
st.markdown("""
# 📊 Retail Pulse – Analítica de Ventas en Tiempo Real
_Demo interactiva con conexión a Square Sandbox_
""")

# Sidebar: Configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    
    sector_key = st.selectbox(
        "Sector de negocio",
        options=list(BENCHMARK_SECTORES.keys()),
        format_func=lambda x: BENCHMARK_SECTORES[x]['nombre']
    )
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", datetime.now().date() - timedelta(days=7))
    with col2:
        fecha_fin = st.date_input("Fecha fin", datetime.now().date())
    
    if st.button("🔄 Sincronizar con Square", type="primary", width='stretch'):
        with st.spinner("Obteniendo datos de Square..."):
            df, mensaje = obtener_datos_square(fecha_inicio, fecha_fin)
            if not df.empty:
                st.session_state['df'] = df
                st.session_state['sector'] = sector_key
                st.session_state['fecha_inicio'] = fecha_inicio
                st.session_state['fecha_fin'] = fecha_fin
                st.success(f"✅ {mensaje} ({len(df)} registros)")
            else:
                st.error(f"❌ {mensaje}")
    
    if st.button("📊 Cargar datos de demostración", width='stretch'):
        df, mensaje = generar_datos_demo(fecha_inicio, fecha_fin)
        if not df.empty:
            st.session_state['df'] = df
            st.session_state['sector'] = sector_key
            st.session_state['fecha_inicio'] = fecha_inicio
            st.session_state['fecha_fin'] = fecha_fin
            st.success(f"✅ {mensaje} ({len(df)} registros)")
    
    # Mostrar estado del token (sin molestar)
    token = obtener_token_square()
    if token:
        st.success("✅ Token de Square configurado")
    else:
        st.info("ℹ️ Sin token de Square (se usarán datos de demostración)")

# ------------------------------------------------------------
# PROCESAMIENTO Y VISUALIZACIÓN DE DATOS
# ------------------------------------------------------------
# Si no hay datos en sesión, cargar automáticamente datos de demostración
if 'df' not in st.session_state:
    fecha_inicio_def = datetime.now().date() - timedelta(days=7)
    fecha_fin_def = datetime.now().date()
    df_demo, _ = generar_datos_demo(fecha_inicio_def, fecha_fin_def)
    st.session_state['df'] = df_demo
    st.session_state['sector'] = 'textil'
    st.session_state['fecha_inicio'] = fecha_inicio_def
    st.session_state['fecha_fin'] = fecha_fin_def

if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    sector_key = st.session_state.get('sector', 'textil')
    fecha_inicio = st.session_state.get('fecha_inicio', datetime.now().date() - timedelta(days=7))
    fecha_fin = st.session_state.get('fecha_fin', datetime.now().date())
    
    # Procesar datos con el motor de KPIs
    resultado = procesar_periodo(df, "PERIODO COMPLETO", sector_key=sector_key)
    
    # ------------------------------------------------------------
    # FILA 1: KPIs principales
    # ------------------------------------------------------------
    st.subheader("📈 KPIs Principales")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Ventas Totales", f"{resultado.get('tot_ventas', '0')} €")
    with col2:
        st.metric("🧾 Transacciones", resultado.get('tot_trans', '0'))
    with col3:
        st.metric("⚡ VPH", f"{resultado.get('vph_global', '0')} €/h")
    with col4:
        st.metric("🔄 Conversión", f"{resultado.get('tasa_conv', '0')}%")
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("🛒 AOV", f"{resultado.get('aov_global', '0')} €")
    with col6:
        st.metric("📦 UPT", resultado.get('upt_global', '0'))
    with col7:
        st.metric("💸 Coste Laboral", f"{resultado.get('coste_lab_pct', '0')}%")
    with col8:
        st.metric("⚠️ Impacto Ineficiencia", f"{resultado.get('impacto_pct', '0')}%")
    
    # ------------------------------------------------------------
    # FILA 2: Gráfico de VPH por Vendedor
    # ------------------------------------------------------------
    st.subheader("⚡ Productividad por Vendedor")
    vendedores = resultado.get('vendedores', [])
    if vendedores:
        df_vph = pd.DataFrame([
            {"Vendedor": v['id'], "VPH": v['vph'], "Cuadrante": v['cuadrante']}
            for v in vendedores
        ])
        df_vph = df_vph.sort_values('VPH', ascending=False)
        
        fig = px.bar(
            df_vph,
            x="Vendedor",
            y="VPH",
            color="Cuadrante",
            color_discrete_sequence=px.colors.qualitative.Set2,
            title="VPH por Vendedor (€/h)",
            text_auto=".1f"
        )
        
        media_vph = float(resultado.get('vph_global', 0))
        fig.add_hline(
            y=media_vph,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Media: {media_vph:.1f} €/h",
            annotation_position="top right"
        )
        
        fig.update_layout(
            height=400,
            xaxis_title="",
            yaxis_title="VPH (€/h)",
            showlegend=True,
            legend_title="Cuadrante"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos de vendedores disponibles.")
    
    # ------------------------------------------------------------
    # FILA 3: Dictamen de Vendedores
    # ------------------------------------------------------------
    with st.expander("👤 Dictamen de Vendedores (clic para desplegar)", expanded=False):
        if vendedores:
            for v in vendedores:
                st.markdown(f"""
                **{v['id']}** – {v['cuadrante']}
                - VPH: {v['vph']} €/h | AOV: {v['aov']} € | UPT: {v['upt']}
                - Venta Neta: {v['venta_neta']} € | Retorno: {v['retorno_pct']}%
                - **Recomendación:** {v['recomendacion']}
                ---
                """)
        else:
            st.info("ℹ️ No hay dictamen disponible.")
    
    # ------------------------------------------------------------
    # FILA 4: Tabla de datos en bruto
    # ------------------------------------------------------------
    with st.expander("📋 Ver datos en bruto (DataFrame)", expanded=False):
        st.dataframe(df)
    
    # ------------------------------------------------------------
    # FILA 5: Descarga de PDF
    # ------------------------------------------------------------
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        nombre_cliente = st.text_input("Nombre del cliente", value="Demo")
    with col2:
        if st.button("📥 Descargar PDF"):
            pdf_buffer = generar_pdf_simple(resultado, fecha_inicio, fecha_fin, nombre_cliente)
            if pdf_buffer:
                st.download_button(
                    label="📄 Descargar PDF",
                    data=pdf_buffer,
                    file_name=f"Retail_Pulse_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

else:
    st.info("ℹ️ No hay datos cargados. Usa el panel de la izquierda para sincronizar con Square o cargar datos de demostración.")

# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------
st.markdown("---")
st.caption("Desarrollado con ❤️ · Demo interactiva con Square Sandbox")
