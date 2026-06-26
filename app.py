import os
import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
import re
import textwrap

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
# CSS LIMPIO (Solo clases para las tarjetas internas)
# ------------------------------------------------------------
st.markdown("""
<style>
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.8rem; margin: 1rem 0; font-family: 'Georgia', serif; }
    .metric-card { background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 0.8rem 1rem; }
    .metric-card:hover { border-color: #f59e0b; background: #1a2332; }
    .metric-name { font-weight: 700; color: #f8fafc; font-size: 0.95rem; display: flex; justify-content: space-between; align-items: center; }
    .metric-def { color: #94a3b8; font-size: 0.8rem; margin: 0.2rem 0; }
    .metric-util { color: #a5b4fc; font-size: 0.75rem; border-top: 1px solid #1e293b; padding-top: 0.3rem; margin-top: 0.3rem; }
    .badge { display: inline-block; background: #1e293b; color: #94a3b8; font-size: 0.65rem; padding: 0.1rem 0.6rem; border-radius: 12px; border: 1px solid #334155; margin-left: 0.5rem; }
    .footer-note { color: #64748b; font-size: 0.8rem; text-align: center; margin-top: 2rem; border-top: 1px solid #1e293b; padding-top: 1.2rem; font-family: sans-serif; }
</style>
""", unsafe_allow_html=True)

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
    try:
        token = st.secrets["SQUARE_ACCESS_TOKEN"]
        if token and token != "tu_token_aqui":
            return token
    except:
        pass
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if token and token != "tu_token_aqui":
        return token
    return None

def obtener_datos_square(fecha_inicio, fecha_fin):
    token = obtener_token_square()
    if not token:
        return generar_datos_demo(fecha_inicio, fecha_fin)
    
    try:
        client = Client(access_token=token, environment="sandbox")
        start_str = fecha_inicio.strftime("%Y-%m-%dT00:00:00Z")
        end_str = fecha_fin.strftime("%Y-%m-%dT23:59:59Z")
        
        with st.spinner("🔄 Obteniendo datos de Square..."):
            result = client.orders.list_orders(
                location_id="main", begin_time=start_str, end_time=end_str, limit=200
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
                
                unidades = sum(int(item.get('quantity', 0)) for item in order.get('line_items', []))
                
                datos.append({
                    "Fecha": fecha, "Vendedor_ID": vendedor, "Ventas": amount,
                    "Transacciones": 1, "Unidades": unidades, "Horas_Trabajadas": 1.0,
                    "Trafico_Tienda": 50, "Coste_Hora": 12.50
                })
            
            df = pd.DataFrame(datos)
            if df.empty:
                return generar_datos_demo(fecha_inicio, fecha_fin)
            return df, "Datos obtenidos correctamente desde Square"
            
    except Exception:
        return generar_datos_demo(fecha_inicio, fecha_fin)

def generar_datos_demo(fecha_inicio, fecha_fin):
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
            
            es_pico = (hora >= 17 and hora <= 20) and (dt.weekday() >= 5)
            es_valle = (hora <= 13) and (dt.weekday() <= 2)
            
            trafico = np.random.randint(100, 160) if es_pico else (np.random.randint(8, 20) if es_valle else np.random.randint(30, 70))
            conv_rate = np.random.uniform(0.25, 0.32) if es_pico else (np.random.uniform(0.40, 0.55) if es_valle else np.random.uniform(0.32, 0.42))
            
            trans_totales = max(1, int(trafico * conv_rate))
            trans_por_v = max(1, trans_totales // num_vendedores)
            
            for v in vendedores_turno:
                aov_base, u_base = (48, 2.9) if "Asesor" in v else ((36, 2.2) if "Senior" in v else ((22, 1.2) if "Cajero" in v else ((18, 1.1) if "Practicante" in v else (20, 1.3))))
                trans = max(1, int(trans_por_v * np.random.uniform(0.7, 1.3)))
                
                datos.append({
                    "Fecha": dt, "Vendedor_ID": v,
                    "Ventas": round(trans * aov_base * np.random.uniform(0.9, 1.1), 2),
                    "Transacciones": trans,
                    "Unidades": max(trans, int(trans * u_base * np.random.uniform(0.9, 1.1))),
                    "Horas_Trabajadas": round(1.0 / num_vendedores, 2),
                    "Trafico_Tienda": trafico, "Coste_Hora": 12.50
                })
    
    return pd.DataFrame(datos), "Datos de demostración generados"

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
        story = [
            Paragraph("INFORME DE AUDITORÍA – RETAIL PULSE", styles['Title']),
            Spacer(1, 0.5*cm),
            Paragraph(f"Cliente: {cliente}", styles['Normal']),
            Paragraph(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}", styles['Normal']),
            Spacer(1, 0.5*cm)
        ]
        
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
            ('BACKGROUND', (0,0), (-1,0), colors.grey), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (1,1), (1,-1), 'RIGHT'),
        ]))
        story.extend([t, Spacer(1, 0.5*cm)])
        
        vendedores = resultado.get('vendedores', [])
        if vendedores:
            story.append(Paragraph("Dictamen por Vendedor", styles['Heading2']))
            for v in vendedores[:3]:
                story.extend([
                    Paragraph(f"<b>{v['id']}</b> – {v['cuadrante']}", styles['Normal']),
                    Paragraph(f"VPH: {v['vph']} €/h | AOV: {v['aov']} € | UPT: {v['upt']}", styles['Normal']),
                    Paragraph(f"<b>Recomendación:</b> {v['recomendacion']}", styles['Normal']),
                    Spacer(1, 0.3*cm)
                ])
        
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer
    except Exception as e:
        st.error(f"Error al generar PDF: {e}")
        return None

# ------------------------------------------------------------
# MAQUETACIÓN HTML INTERNA DEL DIÁLOGO
# ------------------------------------------------------------
def get_metricas_html():
    return textwrap.dedent("""
    <p style="text-align:center; color:#94a3b8; font-size:1.05rem; margin-top:-10px;">
        Retail Pulse v1.0 · Arquitectura modular y versátil
    </p>
    
    <div style="background:#1a2332; border-left:6px solid #f59e0b; padding:1rem 1.5rem; border-radius:10px; margin:1.5rem 0;">
        <p style="margin:0;"><strong>⚡ Versatilidad del modelo</strong></p>
        <p style="color:#d1d5db; font-size:0.95rem; margin-top:0.5rem; margin-bottom:0;">
            Este motor de análisis está diseñado para adaptarse a <strong>cualquier sector retail, tipo de negocio o departamento</strong> (ventas, RRHH, operaciones, etc.). Se puede personalizar mediante la selección de benchmarks sectoriales y parámetros propios.
        </p>
    </div>
    
    <h3 style="color:#38bdf8; border-left:4px solid #38bdf8; padding-left:0.8rem;">📋 Estructura del Informe</h3>
    <ul style="color:#d1d5db; font-size:0.95rem; line-height:1.6; padding-left:1.5rem;">
        <li><strong>Portada</strong> – Título, cliente, período analizado.</li>
        <li><strong>Resumen Global</strong> – Tabla con KPIs principales + comentario automático.</li>
        <li><strong>Dictamen Individualizado por Vendedor</strong> – Lista con métricas clave y recomendación.</li>
        <li><strong>Informe Ejecutivo</strong> (narrativa personalizada de 8 puntos clave).</li>
        <li><strong>Anexo: Gráficos</strong> – Barras VPH, evolución diaria y distribución de ventas.</li>
    </ul>

    <h3 style="color:#38bdf8; border-left:4px solid #38bdf8; padding-left:0.8rem; margin-top:1.5rem;">📈 Métricas Empleadas</h3>
    
    <h4 style="color:#f8fafc; margin-bottom:0.4rem;">🌐 Métricas Globales</h4>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-name">Ventas Totales <span class="badge">Volumen</span></div><div class="metric-def">Facturación bruta acumulada.</div><div class="metric-util">🔹 Tamaño del negocio.</div></div>
        <div class="metric-card"><div class="metric-name">Transacciones <span class="badge">Actividad</span></div><div class="metric-def">Número de tickets emitidos.</div><div class="metric-util">🔹 Volumen de operaciones.</div></div>
        <div class="metric-card"><div class="metric-name">Tráfico Total <span class="badge">Afluencia</span></div><div class="metric-def">Visitas o pases registrados.</div><div class="metric-util">🔹 Base para conversión.</div></div>
        <div class="metric-card"><div class="metric-name">Tasa Conversión <span class="badge">Eficacia</span></div><div class="metric-def">(Transacciones / Tráfico) × 100.</div><div class="metric-util">🔹 % de compra real.</div></div>
        <div class="metric-card"><div class="metric-name">VPH <span class="badge">Productividad</span></div><div class="metric-def">Ventas / Horas trabajadas.</div><div class="metric-util">🔹 KPI rey laboral.</div></div>
        <div class="metric-card"><div class="metric-name">AOV <span class="badge">Valor</span></div><div class="metric-def">Ventas / Transacciones.</div><div class="metric-util">🔹 Gasto medio por ticket.</div></div>
        <div class="metric-card"><div class="metric-name">UPT <span class="badge">Cesta</span></div><div class="metric-def">Unidades / Transacciones.</div><div class="metric-util">🔹 Venta cruzada.</div></div>
        <div class="metric-card"><div class="metric-name">Coste Laboral % <span class="badge">Eficiencia</span></div><div class="metric-def">(Coste salarial / Ventas) × 100.</div><div class="metric-util">🔹 Peso de nóminas.</div></div>
    </div>

    <h4 style="color:#f8fafc; margin-bottom:0.4rem; margin-top:1.2rem;">👤 Métricas por Vendedor</h4>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-name">VPH individual <span class="badge">Productividad</span></div><div class="metric-def">Ventas / Horas del vendedor.</div><div class="metric-util">🔹 Productividad propia.</div></div>
        <div class="metric-card"><div class="metric-name">Venta Neta <span class="badge">Real</span></div><div class="metric-def">Ventas brutas - Devoluciones.</div><div class="metric-util">🔹 Ingreso consolidado.</div></div>
        <div class="metric-card"><div class="metric-name">Tasa de Retorno <span class="badge">Calidad</span></div><div class="metric-def">(Devoluciones / Ventas) × 100.</div><div class="metric-util">🔹 Calidad de venta.</div></div>
        <div class="metric-card"><div class="metric-name">Stress Ratio <span class="badge">Presión</span></div><div class="metric-def">VPH en picos / VPH en valles.</div><div class="metric-util">🔹 Resiliencia en caos.</div></div>
        <div class="metric-card"><div class="metric-name">Cuadrante <span class="badge">Perfil</span></div><div class="metric-def">Clasificación automática.</div><div class="metric-util">🔹 Asesor, Despachador...</div></div>
    </div>

    <div class="footer-note">
        Este modelo es parte de la suite Retail Pulse · Desarrollado para ofrecer análisis profundos.
    </div>
    """)

# ------------------------------------------------------------
# DECLARACIÓN DEL POPUP NATVO DE STREAMLIT
# ------------------------------------------------------------
@st.dialog("📊 MODELO DE ANÁLISIS AVANZADO", width="large")
def abrir_modal_nativo():
    st.markdown(get_metricas_html(), unsafe_allow_html=True)
    st.write("") # Espaciador
    if st.button("✕ Cerrar panel", use_container_width=True):
        st.rerun()


# ------------------------------------------------------------
# INTERFAZ PRINCIPAL DE STREAMLIT
# ------------------------------------------------------------
col_titulo, col_boton = st.columns([4, 1])
with col_titulo:
    st.markdown("""
    # 📊 Retail Pulse – Analítica de Ventas en Tiempo Real
    _Demo interactiva con conexión a Square Sandbox · Datos actualizados al instante_
    """)
with col_boton:
    # Llamamos directamente a la función decorada
    if st.button("📊 Ver modelo y métricas", key="btn_metricas"):
        abrir_modal_nativo()

# Sidebar: Configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    sector_key = st.selectbox("Sector de negocio", options=list(BENCHMARK_SECTORES.keys()), format_func=lambda x: BENCHMARK_SECTORES[x]['nombre'])
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", datetime.now().date() - timedelta(days=7))
    with col2:
        fecha_fin = st.date_input("Fecha fin", datetime.now().date())
    
    if st.button("🔄 Sincronizar con Square", type="primary", use_container_width=True):
        with st.spinner("Obteniendo datos de Square..."):
            df, mensaje = obtener_datos_square(fecha_inicio, fecha_fin)
            if not df.empty:
                st.session_state['df'] = df; st.session_state['sector'] = sector_key
                st.session_state['fecha_inicio'] = fecha_inicio; st.session_state['fecha_fin'] = fecha_fin
                st.success(f"✅ {mensaje} ({len(df)} registros)")
            else:
                st.error(f"❌ {mensaje}")
    
    if st.button("📊 Cargar datos de demostración", use_container_width=True):
        df, mensaje = generar_datos_demo(fecha_inicio, fecha_fin)
        if not df.empty:
            st.session_state['df'] = df; st.session_state['sector'] = sector_key
            st.session_state['fecha_inicio'] = fecha_inicio; st.session_state['fecha_fin'] = fecha_fin
            st.success(f"✅ {mensaje} ({len(df)} registros)")
    
    st.success("✅ Token de Square configurado") if obtener_token_square() else st.info("ℹ️ Sin token (Modo Demo)")

# ------------------------------------------------------------
# PROCESAMIENTO Y VISUALIZACIÓN DE DATOS
# ------------------------------------------------------------
if 'df' not in st.session_state:
    f_ini, f_fin = datetime.now().date() - timedelta(days=7), datetime.now().date()
    st.session_state['df'], _ = generar_datos_demo(f_ini, f_fin)
    st.session_state['sector'] = 'textil'; st.session_state['fecha_inicio'] = f_ini; st.session_state['fecha_fin'] = f_fin

if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    res = procesar_periodo(df, "PERIODO COMPLETO", sector_key=st.session_state.get('sector', 'textil'))
    
    st.subheader("📈 KPIs Principales")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Ventas Totales", f"{res.get('tot_ventas', '0')} €")
    c2.metric("🧾 Transacciones", res.get('tot_trans', '0'))
    c3.metric("⚡ VPH", f"{res.get('vph_global', '0')} €/h")
    c4.metric("🔄 Conversión", f"{res.get('tasa_conv', '0')}%")
    
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("🛒 AOV", f"{res.get('aov_global', '0')} €")
    c6.metric("📦 UPT", res.get('upt_global', '0'))
    c7.metric("💸 Coste Laboral", f"{res.get('coste_lab_pct', '0')}%")
    c8.metric("⚠️ Impacto Ineficiencia", f"{res.get('impacto_pct', '0')}%")
    
    st.subheader("⚡ Productividad por Vendedor")
    vendedores = res.get('vendedores', [])
    if vendedores:
        df_vph = pd.DataFrame([{"Vendedor": v['id'], "VPH": v['vph'], "Cuadrante": v['cuadrante']} for v in vendedores]).sort_values('VPH', ascending=False)
        fig = px.bar(df_vph, x="Vendedor", y="VPH", color="Cuadrante", color_discrete_sequence=px.colors.qualitative.Set2, text_auto=".1f")
        fig.add_hline(y=float(res.get('vph_global', 0)), line_dash="dash", line_color="red", annotation_text=f"Media: {float(res.get('vph_global', 0)):.1f} €/h")
        fig.update_layout(height=400, xaxis_title="", yaxis_title="VPH (€/h)")
        st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("👤 Dictamen de Vendedores (clic para desplegar)"):
        for v in vendedores:
            st.markdown(f"**{v['id']}** – {v['cuadrante']}\n- VPH: {v['vph']} €/h | AOV: {v['aov']} € | UPT: {v['upt']}\n- **Recomendación:** {v['recomendacion']}\n---") if vendedores else st.info("Sin datos.")
    
    with st.expander("📋 Ver datos en bruto (DataFrame)"):
        st.dataframe(df)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        n_cli = st.text_input("Nombre del cliente", value="Demo")
    with col2:
        if st.button("📥 Descargar PDF"):
            if pdf_buf := generar_pdf_simple(res, st.session_state['fecha_inicio'], st.session_state['fecha_fin'], n_cli):
                st.download_button("📄 Descargar archivo", data=pdf_buf, file_name="Retail_Pulse.pdf", mime="application/pdf")

# ------------------------------------------------------------
# FOOTER MULTI-TEMA (Visible siempre)
# ------------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; font-size: 0.9rem; color: #64748b;">
    Desarrollado por <strong style="color: #f59e0b;">Jose Luis Asenjo</strong> · 
    <a href="mailto:asenjo.jose@hotmail.com" style="color: #38bdf8; text-decoration: none; font-weight: 500;">asenjo.jose@hotmail.com</a>
</div>
""", unsafe_allow_html=True)
