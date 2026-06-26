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
# CSS PARA EL MODAL
# ------------------------------------------------------------
st.markdown("""
<style>
    /* Fondo del modal (overlay) */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
    }
    /* Contenido del modal */
    .modal-content {
        background: #111827;
        color: #f8fafc;
        border: 1px solid #1e293b;
        border-radius: 16px;
        max-width: 900px;
        width: 100%;
        max-height: 85vh;
        overflow-y: auto;
        padding: 2rem 2rem 1.5rem 2rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.8);
        font-family: 'Georgia', 'Cardo', serif;
        position: relative;
    }
    .modal-content h2 {
        color: #f59e0b;
        text-align: center;
        font-size: 1.8rem;
        border-bottom: 2px solid #f59e0b33;
        padding-bottom: 0.8rem;
        margin-bottom: 1.5rem;
    }
    .modal-content h3 {
        color: #38bdf8;
        font-size: 1.2rem;
        margin-top: 1.8rem;
        border-left: 4px solid #38bdf8;
        padding-left: 0.8rem;
    }
    .modal-content .badge {
        display: inline-block;
        background: #1e293b;
        color: #94a3b8;
        font-size: 0.65rem;
        padding: 0.1rem 0.6rem;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-left: 0.5rem;
    }
    .modal-content .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 0.8rem;
        margin: 1rem 0;
    }
    .modal-content .metric-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 0.8rem 1rem;
    }
    .modal-content .metric-card:hover {
        border-color: #f59e0b;
        background: #1a2332;
    }
    .modal-content .metric-name {
        font-weight: 700;
        color: #f8fafc;
        font-size: 0.95rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .modal-content .metric-def {
        color: #94a3b8;
        font-size: 0.8rem;
        margin: 0.2rem 0;
    }
    .modal-content .metric-util {
        color: #a5b4fc;
        font-size: 0.75rem;
        border-top: 1px solid #1e293b;
        padding-top: 0.3rem;
        margin-top: 0.3rem;
    }
    .modal-content .close-btn {
        background: #f59e0b;
        color: #0b0f19;
        font-weight: bold;
        border: none;
        padding: 0.6rem 2rem;
        border-radius: 30px;
        font-size: 0.9rem;
        cursor: pointer;
        margin-top: 1.5rem;
        display: inline-block;
    }
    .modal-content .close-btn:hover {
        background: #d97706;
    }
    .modal-content .footer-note {
        color: #64748b;
        font-size: 0.8rem;
        text-align: center;
        margin-top: 2rem;
        border-top: 1px solid #1e293b;
        padding-top: 1.2rem;
    }
    .btn-metricas {
        background: #f59e0b;
        color: #0b0f19;
        padding: 0.4rem 1.2rem;
        border-radius: 30px;
        font-weight: bold;
        font-size: 0.85rem;
        border: none;
        cursor: pointer;
        transition: background 0.2s;
        display: inline-block;
    }
    .btn-metricas:hover {
        background: #d97706;
    }
    /* Scrollbar */
    .modal-content::-webkit-scrollbar {
        width: 6px;
    }
    .modal-content::-webkit-scrollbar-track {
        background: #1e293b;
        border-radius: 10px;
    }
    .modal-content::-webkit-scrollbar-thumb {
        background: #f59e0b;
        border-radius: 10px;
    }
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
                    aov_base = 48; u_base = 2.9
                elif "Senior" in v:
                    aov_base = 36; u_base = 2.2
                elif "Cajero" in v:
                    aov_base = 22; u_base = 1.2
                elif "Practicante" in v:
                    aov_base = 18; u_base = 1.1
                else:
                    aov_base = 20; u_base = 1.3
                
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
# FUNCIÓN PARA GENERAR EL CONTENIDO DEL MODAL (INFOGRAFÍA)
# ------------------------------------------------------------
def get_metricas_html():
    return """
    <h2>📊 MODELO DE ANÁLISIS AVANZADO</h2>
    <p style="text-align:center; color:#94a3b8; font-size:1.05rem;">
        Retail Pulse v1.0 · Arquitectura modular y versátil
    </p>
    
    <div style="background:#1a2332; border-left:6px solid #f59e0b; padding:1rem 1.5rem; border-radius:10px; margin:1.5rem 0;">
        <p><strong>⚡ Versatilidad del modelo</strong></p>
        <p style="color:#d1d5db; font-size:0.95rem;">
            Este motor de análisis está diseñado para adaptarse a <strong>cualquier sector retail, tipo de negocio o departamento</strong> (ventas, RRHH, operaciones, etc.).
            Se puede personalizar mediante la selección de <strong>benchmarks sectoriales</strong> y la configuración de <strong>parámetros propios</strong>.
            Es aplicable a tiendas físicas, e-commerce, equipos comerciales, y cualquier entorno donde se quiera medir la eficiencia y productividad de la fuerza de ventas.
        </p>
    </div>
    
    <h3>📋 Estructura del Informe Generado</h3>
    <ul style="color:#d1d5db; font-size:0.95rem; line-height:1.6; list-style-type:decimal; padding-left:1.5rem;">
        <li><strong>Portada</strong> – Título, cliente, período analizado.</li>
        <li><strong>Resumen Global</strong> – Tabla con KPIs principales + comentario automático.</li>
        <li><strong>Dictamen Individualizado por Vendedor</strong> – Lista de cada vendedor con métricas clave y recomendación. Incluye leyenda de perfiles.</li>
        <li><strong>Informe Ejecutivo</strong> (narrativa personalizada):
            <ul>
                <li>3.1. Visión Global de la Tienda</li>
                <li>3.2. Análisis de la Matriz de Calor y Patrones de Demanda</li>
                <li>3.3. Rendimiento Individual por Vendedor (con apodos y comentarios)</li>
                <li>3.4. Ineficiencia y Oportunidad Perdida</li>
                <li>3.5. Gestión de Stock y Devoluciones</li>
                <li>3.6. Benchmarking Sectorial (Nacional y, opcional, Regional)</li>
                <li>3.7. Conclusiones Estratégicas y Plan de Acción</li>
                <li>3.8. Proyección de Mejora</li>
            </ul>
        </li>
        <li><strong>Contexto Regional</strong> (opcional) – Datos del entorno geográfico, marco laboral, digitalización, etc.</li>
        <li><strong>Anexo: Gráficos</strong> – Barras VPH, evolución diaria, torta de distribución de ventas.</li>
    </ul>

    <h3>📈 Métricas Empleadas (Definición y Utilidad)</h3>
    <p style="color:#94a3b8;">Todas las métricas que se calculan y presentan en el informe, agrupadas por categorías.</p>
    
    <h4>🌐 Métricas Globales</h4>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-name">Ventas Totales <span class="badge">Volumen</span></div><div class="metric-def">Facturación bruta acumulada.</div><div class="metric-util">🔹 Indica el tamaño del negocio.</div></div>
        <div class="metric-card"><div class="metric-name">Transacciones <span class="badge">Actividad</span></div><div class="metric-def">Número de tickets/recibos emitidos.</div><div class="metric-util">🔹 Mide el volumen de operaciones.</div></div>
        <div class="metric-card"><div class="metric-name">Tráfico Total <span class="badge">Afluencia</span></div><div class="metric-def">Número de visitas o pases registrados.</div><div class="metric-util">🔹 Base para calcular la conversión.</div></div>
        <div class="metric-card"><div class="metric-name">Tasa de Conversión <span class="badge">Eficacia</span></div><div class="metric-def">(Transacciones / Tráfico) × 100.</div><div class="metric-util">🔹 Porcentaje de visitantes que compran.</div></div>
        <div class="metric-card"><div class="metric-name">VPH <span class="badge">Productividad</span></div><div class="metric-def">Ventas totales / Horas trabajadas.</div><div class="metric-util">🔹 KPI principal de productividad laboral.</div></div>
        <div class="metric-card"><div class="metric-name">AOV <span class="badge">Valor</span></div><div class="metric-def">Ventas totales / Transacciones.</div><div class="metric-util">🔹 Gasto promedio por compra.</div></div>
        <div class="metric-card"><div class="metric-name">UPT <span class="badge">Cesta</span></div><div class="metric-def">Unidades totales / Transacciones.</div><div class="metric-util">🔹 Artículos por ticket (cross-selling).</div></div>
        <div class="metric-card"><div class="metric-name">Coste Laboral % <span class="badge">Eficiencia</span></div><div class="metric-def">(Coste salarial / Ventas) × 100.</div><div class="metric-util">🔹 Peso de los salarios sobre la facturación.</div></div>
        <div class="metric-card"><div class="metric-name">Impacto Ineficiencia <span class="badge">Fuga</span></div><div class="metric-def">(Idle Cost + COP) / Ventas × 100.</div><div class="metric-util">🔹 Ventas perdidas por mala gestión.</div></div>
        <div class="metric-card"><div class="metric-name">Coste de Oportunidad <span class="badge">Pérdida</span></div><div class="metric-def">Clientes perdidos × AOV × Margen.</div><div class="metric-util">🔹 Ventas potenciales no realizadas en picos.</div></div>
        <div class="metric-card"><div class="metric-name">Coste de Ocio <span class="badge">Sobrepersonal</span></div><div class="metric-def">Gasto salarial en horas de baja afluencia.</div><div class="metric-util">🔹 Indica exceso de personal en momentos de poco tráfico.</div></div>
        <div class="metric-card"><div class="metric-name">Clientes Perdidos <span class="badge">Oportunidad</span></div><div class="metric-def">Estimación de clientes que no compraron en picos.</div><div class="metric-util">🔹 Cuantifica la pérdida real de negocio.</div></div>
        <div class="metric-card"><div class="metric-name">Ratio Staff-Tráfico <span class="badge">Cobertura</span></div><div class="metric-def">Tráfico en picos / Horas trabajadas en picos.</div><div class="metric-util">🔹 Clientes por empleado en horas punta.</div></div>
        <div class="metric-card"><div class="metric-name">Déficit de horas en picos <span class="badge">Staffing</span></div><div class="metric-def">(Tráfico pico / Traf_opt_empleado) - Horas pico reales.</div><div class="metric-util">🔹 Horas de personal que faltaron para cubrir la demanda.</div></div>
        <div class="metric-card"><div class="metric-name">Margen Bruto aplicado <span class="badge">COP</span></div><div class="metric-def">Porcentaje de margen usado para calcular el COP.</div><div class="metric-util">🔹 Ajustable por el usuario.</div></div>
        <div class="metric-card"><div class="metric-name">Rotación de Stock <span class="badge">Inventario</span></div><div class="metric-def">Ventas (€) / Stock promedio (unidades).</div><div class="metric-util">🔹 Frecuencia de renovación del inventario en valor.</div></div>
    </div>

    <h4>👤 Métricas por Vendedor</h4>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-name">VPH individual <span class="badge">Productividad</span></div><div class="metric-def">Ventas del vendedor / Horas del vendedor.</div><div class="metric-util">🔹 Compara productividad individual.</div></div>
        <div class="metric-card"><div class="metric-name">AOV individual <span class="badge">Valor</span></div><div class="metric-def">Ventas / Transacciones del vendedor.</div><div class="metric-util">🔹 Capacidad de generar tickets de alto valor.</div></div>
        <div class="metric-card"><div class="metric-name">UPT individual <span class="badge">Cesta</span></div><div class="metric-def">Unidades / Transacciones del vendedor.</div><div class="metric-util">🔹 Habilidad de venta cruzada.</div></div>
        <div class="metric-card"><div class="metric-name">Venta Neta <span class="badge">Real</span></div><div class="metric-def">Ventas brutas - Devoluciones.</div><div class="metric-util">🔹 Ingreso real después de devoluciones.</div></div>
        <div class="metric-card"><div class="metric-name">Tasa de Retorno <span class="badge">Calidad</span></div><div class="metric-def">(Devoluciones / Ventas) × 100.</div><div class="metric-util">🔹 Porcentaje de productos devueltos.</div></div>
        <div class="metric-card"><div class="metric-name">REP % <span class="badge">Eficiencia salarial</span></div><div class="metric-def">(Coste salarial / Ventas) × 100.</div><div class="metric-util">🔹 Peso del salario sobre su facturación.</div></div>
        <div class="metric-card"><div class="metric-name">Sell-through <span class="badge">Rotación</span></div><div class="metric-def">(Unidades vendidas / Stock promedio) × 100.</div><div class="metric-util">🔹 Capacidad de mover inventario.</div></div>
        <div class="metric-card"><div class="metric-name">Stress Ratio <span class="badge">Comportamiento</span></div><div class="metric-def">VPH en picos / VPH en valles.</div><div class="metric-util">🔹 Resiliencia bajo presión (>1,05 mejora; <0,85 colapsa).</div></div>
        <div class="metric-card"><div class="metric-name">Fidelización <span class="badge">Lealtad</span></div><div class="metric-def">(Tickets socio / Transacciones) × 100.</div><div class="metric-util">🔹 Porcentaje de clientes recurrentes.</div></div>
        <div class="metric-card"><div class="metric-name">Horas en Pico/Valle <span class="badge">Contexto</span></div><div class="metric-def">Distribución de horas en alta/baja afluencia.</div><div class="metric-util">🔹 Contextualiza el rendimiento.</div></div>
        <div class="metric-card"><div class="metric-name">Peso Operativo <span class="badge">Carga</span></div><div class="metric-def">(Horas del vendedor / Horas totales) × 100.</div><div class="metric-util">🔹 Proporción de horas que aporta al equipo.</div></div>
        <div class="metric-card"><div class="metric-name">Cuadrante Comercial <span class="badge">Perfil</span></div><div class="metric-def">Clasificación automática (ASESOR TOP, DESPACHADOR, etc.).</div><div class="metric-util">🔹 Resume perfil y sugiere acciones formativas.</div></div>
    </div>

    <h4>📊 Benchmarking y Contexto Sectorial</h4>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-name">Benchmark Conversión <span class="badge">Sector</span></div><div class="metric-def">Conversión objetivo del sector (percentil 50).</div><div class="metric-util">🔹 Referencia para comparar.</div></div>
        <div class="metric-card"><div class="metric-name">Benchmark AOV <span class="badge">Sector</span></div><div class="metric-def">Ticket medio objetivo del sector.</div><div class="metric-util">🔹 Referencia para evaluar ticket medio.</div></div>
        <div class="metric-card"><div class="metric-name">Benchmark UPT <span class="badge">Sector</span></div><div class="metric-def">Unidades por ticket objetivo del sector.</div><div class="metric-util">🔹 Referencia para evaluar venta cruzada.</div></div>
        <div class="metric-card"><div class="metric-name">Tráfico Óptimo/Empleado <span class="badge">Sector</span></div><div class="metric-def">Clientes que un empleado puede atender eficientemente.</div><div class="metric-util">🔹 Base para calcular déficit de horas.</div></div>
        <div class="metric-card"><div class="metric-name">Diferencia vs Benchmark <span class="badge">Desviación</span></div><div class="metric-def">Desviación de la tienda respecto al sector.</div><div class="metric-util">🔹 Indica posición competitiva.</div></div>
    </div>

    <h4>📦 Stock y Devoluciones</h4>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-name">Devoluciones Totales <span class="badge">Calidad</span></div><div class="metric-def">Número total de productos devueltos.</div><div class="metric-util">🔹 Indicador de calidad y satisfacción.</div></div>
        <div class="metric-card"><div class="metric-name">Stock Promedio <span class="badge">Inventario</span></div><div class="metric-def">Media de unidades de stock disponible.</div><div class="metric-util">🔹 Dimensiona el inventario.</div></div>
        <div class="metric-card"><div class="metric-name">Antigüedad Media del Stock <span class="badge">Rotación</span></div><div class="metric-def">Edad media (en meses) del inventario.</div><div class="metric-util">🔹 Si es elevada, indica productos de lenta rotación.</div></div>
    </div>

    <div style="margin-top:1.5rem; background:#0f172a; border-radius:12px; padding:1rem; border:1px solid #1e293b;">
        <p style="color:#d1d5db; text-align:center; font-size:0.9rem;">
            El sistema calcula y presenta <strong>más de 40 métricas</strong> agrupadas en estas categorías. 
            Todas ellas se utilizan en el informe para ofrecer un análisis completo y accionable de la fuerza de ventas.
        </p>
    </div>
    <div style="text-align:center; margin-top:1.5rem;">
        <button class="close-btn" onclick="parent.document.querySelector('.modal-overlay').style.display='none'">✕ Cerrar</button>
    </div>
    <div class="footer-note">
        Este modelo es parte de la suite Retail Pulse · Desarrollado para ofrecer análisis profundos y accionables en el sector retail.
    </div>
    """

# ------------------------------------------------------------
# INTERFAZ PRINCIPAL DE STREAMLIT
# ------------------------------------------------------------

# Título y botón de métricas (en la misma fila)
col_titulo, col_boton = st.columns([4, 1])
with col_titulo:
    st.markdown("""
    # 📊 Retail Pulse – Analítica de Ventas en Tiempo Real
    _Demo interactiva con conexión a Square Sandbox · Datos actualizados al instante_
    """)
with col_boton:
    # Botón para abrir el modal
    if st.button("📊 Ver modelo y métricas", key="btn_metricas"):
        st.session_state['show_modal'] = True

# Mostrar el modal si la variable de sesión está activa
if st.session_state.get('show_modal', False):
    # Inyectamos el HTML del modal con un overlay
    st.markdown(f"""
    <div class="modal-overlay" id="modal-overlay">
        <div class="modal-content">
            {get_metricas_html()}
        </div>
    </div>
    <script>
        // Cerrar el modal al hacer clic fuera del contenido
        document.getElementById('modal-overlay').addEventListener('click', function(e) {{
            if (e.target === this) {{
                this.style.display = 'none';
                // También debemos resetear la variable de sesión en Streamlit
                // Para ello, redirigimos a la misma página con un parámetro
                window.location.href = window.location.pathname + '?close_modal=true';
            }}
        }});
        // Si la URL tiene ?close_modal=true, recargamos sin el parámetro
        if (window.location.search.includes('close_modal=true')) {{
            window.location.href = window.location.pathname;
        }}
    </script>
    """, unsafe_allow_html=True)
    # Resetear la variable de sesión para que no se muestre al recargar
    # (se hará con el script de redirección)

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
    
    token = obtener_token_square()
    if token:
        st.success("✅ Token de Square configurado")
    else:
        st.info("ℹ️ Sin token de Square (se usarán datos de demostración)")

# ------------------------------------------------------------
# PROCESAMIENTO Y VISUALIZACIÓN DE DATOS
# ------------------------------------------------------------
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
    
    resultado = procesar_periodo(df, "PERIODO COMPLETO", sector_key=sector_key)
    
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
        fig.update_layout(height=400, xaxis_title="", yaxis_title="VPH (€/h)", showlegend=True, legend_title="Cuadrante")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos de vendedores disponibles.")
    
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
    
    with st.expander("📋 Ver datos en bruto (DataFrame)", expanded=False):
        st.dataframe(df)
    
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
# FOOTER (actualizado)
# ------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #94a3b8; font-size: 0.9rem;">
        Desarrollado por <strong style="color: #f8fafc;">Jose Luis Asenjo</strong> · 
        <a href="mailto:asenjo.jose@hotmail.com" style="color: #94a3b8; text-decoration: none;">asenjo.jose@hotmail.com</a>
    </div>
    """,
    unsafe_allow_html=True
)
