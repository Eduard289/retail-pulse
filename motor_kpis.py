# =====================================================================
# RETAIL SHIFT AUDITOR - MOTOR DE ANÁLISIS DE KPIs
# Copyright (c) 2025 [Tu nombre]. Todos los derechos reservados.
# Este código es parte del proyecto Retail Pulse y está protegido
# por derechos de autor. No puede ser utilizado sin autorización.
# =====================================================================
# =====================================================================
# RETAIL SHIFT AUDITOR - KPI ANALYSIS ENGINE
# Copyright (c) 2025 [Your Name]. All rights reserved.
# This code is part of the Retail Pulse project and is protected
# by copyright law. It may not be used, copied, or distributed
# without explicit authorization.
# =====================================================================

import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# =====================================================================
# 0. BASE DE DATOS DE INTELIGENCIA COMPETITIVA (Percentiles P50 INE/Sectores)
# =====================================================================
BENCHMARK_SECTORES = {
    "textil":        {"nombre": "Moda, Calzado & Complementos",    "conv": 22.0, "upt": 1.85, "aov": 38.00,  "traf_opt_empleado": 15},
    "gran_consumo":  {"nombre": "Supermercados & Gran Consumo",    "conv": 88.0, "upt": 4.50, "aov": 19.50,  "traf_opt_empleado": 25},
    "salud_belleza": {"nombre": "Salud, Belleza & Parafarmacia",   "conv": 35.0, "upt": 2.40, "aov": 24.00,  "traf_opt_empleado": 18},
    "tecnologia":    {"nombre": "Tecnología & Telecomunicaciones", "conv": 14.0, "upt": 1.30, "aov": 145.00, "traf_opt_empleado": 8},
    "hogar_brico":   {"nombre": "Bricolaje, Mueble & Hogar",       "conv": 48.0, "upt": 2.10, "aov": 65.00,  "traf_opt_empleado": 12},
    "lujo_joyas":    {"nombre": "Lujo, Joyería & Premium",         "conv": 4.5,  "upt": 1.10, "aov": 450.00, "traf_opt_empleado": 4},
    "deportes":      {"nombre": "Deporte & Outdoor",               "conv": 26.0, "upt": 2.10, "aov": 42.00,  "traf_opt_empleado": 16},
    "custom":        {"nombre": "Baremo Personalizado (Manual)",   "conv": 20.0, "upt": 2.00, "aov": 40.00,  "traf_opt_empleado": 15}
}

# =====================================================================
# 1. MOTOR DE SIMULACIÓN TPV
# =====================================================================
def generar_datos_simulados():
    np.random.seed(42)
    fechas_base = pd.date_range(start="2026-06-01 10:00", end="2026-06-30 20:00", freq="h")
    fechas_comerciales = [f for f in fechas_base if 10 <= f.hour <= 20]
    vendedores_pool = ["Vendedor_1 (Junior)", "Vendedor_2 (Senior)", "Vendedor_3 (Cajero)", "Vendedor_4 (Asesor)"]
    datos_mensuales = []
    
    for dt in fechas_comerciales:
        es_pico = dt.dayofweek in [4, 5] and dt.hour >= 17
        es_valle = dt.dayofweek in [0, 1, 2] and dt.hour < 13
        trafico = np.random.randint(80, 135) if es_pico else (np.random.randint(10, 22) if es_valle else np.random.randint(30, 65))
        conv_rate = np.random.uniform(0.29, 0.35) if es_pico else (np.random.uniform(0.42, 0.55) if es_valle else np.random.uniform(0.35, 0.42))
        
        trans_totales = max(1, int(trafico * conv_rate))
        t_count = np.random.randint(1, 4)
        trans_por_v = max(1, trans_totales // t_count)
        
        for _ in range(t_count):
            v_id = np.random.choice(vendedores_pool)
            aov_base = 45.0 if "Asesor" in v_id else (35.0 if "Senior" in v_id else 20.0)
            u_base   = 2.8  if "Asesor" in v_id else (2.1  if "Senior" in v_id else 1.2)
            trans = max(1, int(trans_por_v * np.random.uniform(0.8, 1.2)))
            
            datos_mensuales.append({
                "Fecha": dt.strftime("%Y-%m-%d %H:%M"), "Vendedor_ID": v_id,
                "Ventas": round(trans * aov_base * np.random.uniform(0.9, 1.1), 2),
                "Transacciones": trans, "Unidades": max(trans, int(trans * u_base * np.random.uniform(0.9, 1.1))),
                "Horas_Trabajadas": round(1.0 / t_count, 2), "Trafico_Tienda": trafico, "Coste_Hora": 12.50
            })
    return pd.DataFrame(datos_mensuales)

# =====================================================================
# 2. CAPA ANALÍTICA VECTORIAL (Con Sanitización y Margen Ajustable)
# =====================================================================
def validar_esquema_datos(df):
    df = df.copy() 
    
    req = ['Fecha', 'Vendedor_ID', 'Ventas', 'Transacciones', 'Unidades', 'Horas_Trabajadas', 'Trafico_Tienda', 'Coste_Hora']
    faltantes = [c for c in req if c not in df.columns]
    if faltantes: 
        raise ValueError(f"Columnas faltantes: {faltantes}")
    
    errores = []
    
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    nans_fecha = df['Fecha'].isna().sum()
    if nans_fecha > 0:
        errores.append(f"Se descartaron {nans_fecha} filas por tener un formato de fecha ilegible.")
        df = df.dropna(subset=['Fecha']).copy()

    for col in req[2:]: 
        df[col] = pd.to_numeric(df[col], errors='coerce')
        nans_col = df[col].isna().sum()
        if nans_col > 0:
            errores.append(f"Columna '{col}': {nans_col} celdas contenían texto y fueron convertidas a 0.")
            df[col] = df[col].fillna(0)
    
    for opt in ['Stock_Promedio', 'Devoluciones', 'Antiguedad_Meses', 'Tickets_Socio']:
        if opt in df.columns: 
            df[opt] = pd.to_numeric(df[opt], errors='coerce').fillna(0)
            
    if (df['Ventas'] < 0).any():
        errores.append("Aviso: Se detectaron importes de 'Ventas' negativos.")

    return df, errores

def procesar_periodo(df_slice, nombre_etiqueta, sector_key="textil", custom_bm=None, margen_bruto=0.80):
    if df_slice.empty:
        raise ValueError(f"No hay datos en el rango de fechas para: {nombre_etiqueta}")
    
    # Validar margen_bruto
    if margen_bruto is None or margen_bruto <= 0:
        margen_bruto = 0.80
    margen_bruto = min(margen_bruto, 1.0)  # No puede superar el 100%

    tot_ventas = float(df_slice['Ventas'].sum())
    tot_trans  = int(df_slice['Transacciones'].sum())
    tot_unids  = int(df_slice['Unidades'].sum())
    tot_horas  = float(df_slice['Horas_Trabajadas'].sum())
    tot_coste_lab = float((df_slice['Horas_Trabajadas'] * df_slice['Coste_Hora']).sum())
    
    df_trafico_horario = df_slice.groupby(df_slice['Fecha'].dt.floor('h'))['Trafico_Tienda'].max().fillna(0)
    tot_trafico = int(df_trafico_horario.sum())
    
    coste_lab_pct = (tot_coste_lab / tot_ventas) * 100 if tot_ventas > 0 else 0.0
    tasa_conv_global = (tot_trans / tot_trafico) * 100 if tot_trafico > 0 else 0.0
    vph_global = tot_ventas / tot_horas if tot_horas > 0 else 0.0
    aov_global = tot_ventas / tot_trans if tot_trans > 0 else 0.0
    upt_global = tot_unids / tot_trans if tot_trans > 0 else 0.0
    
    fecha_inicio = df_slice['Fecha'].min().strftime('%d/%m/%Y')
    fecha_fin = df_slice['Fecha'].max().strftime('%d/%m/%Y')
    
    bm = BENCHMARK_SECTORES.get(sector_key, BENCHMARK_SECTORES["textil"])
    if sector_key == "custom" and custom_bm:
        bm_nombre = "Baremo Personalizado"
        bm_conv, bm_upt, bm_aov = float(custom_bm.get('conv', 20)), float(custom_bm.get('upt', 2.0)), float(custom_bm.get('aov', 40))
        bm_traf_emp = int(custom_bm.get('traf_opt_empleado', 15))
    else:
        bm_nombre, bm_conv, bm_upt, bm_aov = bm['nombre'], bm['conv'], bm['upt'], bm['aov']
        bm_traf_emp = bm['traf_opt_empleado']

    df_horas = df_slice.groupby(df_slice['Fecha'].dt.floor('h')).agg({
        'Trafico_Tienda': 'first', 'Horas_Trabajadas': 'sum', 'Coste_Hora': 'max', 'Transacciones': 'sum', 'Ventas': 'sum'
    }).reset_index()

    p75_traf = df_horas['Trafico_Tienda'].quantile(0.75) if not df_horas.empty else 0
    mask_pico = df_horas['Trafico_Tienda'] > p75_traf
    
    traf_pico_tot = float(df_horas.loc[mask_pico, 'Trafico_Tienda'].sum())
    horas_pico_tot = float(df_horas.loc[mask_pico, 'Horas_Trabajadas'].sum())
    ratio_staff_trafico = (traf_pico_tot / horas_pico_tot) if horas_pico_tot > 0 else 0.0
    
    horas_necesarias_pico = (traf_pico_tot / bm_traf_emp) if bm_traf_emp > 0 else horas_pico_tot
    deficit_horas_pico = max(0.0, float(horas_necesarias_pico - horas_pico_tot))

    df_horas['Pers_Necesario'] = np.maximum(1, np.ceil(df_horas['Trafico_Tienda'] / bm_traf_emp))
    exceso_bruto = np.maximum(0, df_horas['Horas_Trabajadas'] - df_horas['Pers_Necesario'])
    df_horas['Horas_Ociosas'] = np.where(exceso_bruto < 0.5, 0.0, exceso_bruto)
    idle_cost = float((df_horas['Horas_Ociosas'] * df_horas['Coste_Hora']).sum())

    df_horas['Conv_Hora'] = (df_horas['Transacciones'] / df_horas['Trafico_Tienda'].replace(0, np.nan)).fillna(0)
    conv_media_pico = df_horas.loc[mask_pico, 'Conv_Hora'].mean() if mask_pico.any() else 0.30
    umbral_conv_dinamico = max(0.10, conv_media_pico * 0.90)

    df_horas['Clientes_Perdidos'] = 0.0
    mask_fuga = mask_pico & (df_horas['Conv_Hora'] < umbral_conv_dinamico)
    df_horas.loc[mask_fuga, 'Clientes_Perdidos'] = np.maximum(0, (df_horas.loc[mask_fuga, 'Trafico_Tienda'] * umbral_conv_dinamico) - df_horas.loc[mask_fuga, 'Transacciones'])

    clientes_perdidos_total = float(df_horas['Clientes_Perdidos'].sum())
    cop_cost = clientes_perdidos_total * (aov_global * margen_bruto)
    impacto_pct = ((idle_cost + cop_cost) / tot_ventas) * 100 if tot_ventas > 0 else 0.0

    p80_traf, p20_traf = df_slice['Trafico_Tienda'].quantile(0.80), df_slice['Trafico_Tienda'].quantile(0.20)
    
    agg_cols = {'Ventas': 'sum', 'Transacciones': 'sum', 'Unidades': 'sum', 'Horas_Trabajadas': 'sum', 'Coste_Hora': 'mean'}
    for opc in ['Devoluciones', 'Stock_Promedio', 'Tickets_Socio']:
        if opc in df_slice.columns: agg_cols[opc] = 'mean' if opc == 'Stock_Promedio' else 'sum'

    df_v = df_slice.groupby('Vendedor_ID').agg(agg_cols).reset_index()
    vendedores_data, lineas_dictamen = [], []
    
    for _, r in df_v.iterrows():
        v_id = str(r['Vendedor_ID'])
        v_ventas_brutas = float(r['Ventas'])
        v_horas = float(r['Horas_Trabajadas'])
        v_trans = int(r['Transacciones'])
        v_unids = int(r['Unidades'])
        v_coste_h = float(r['Coste_Hora'])
        
        v_upt = v_unids / v_trans if v_trans > 0 else 0.0
        v_aov = v_ventas_brutas / v_trans if v_trans > 0 else 0.0
        v_vph = v_ventas_brutas / v_horas if v_horas > 0 else 0.0
        
        v_devs = float(r.get('Devoluciones', 0.0))
        v_venta_neta = max(0.0, v_ventas_brutas - v_devs)
        tasa_retorno = (v_devs / v_ventas_brutas) * 100 if v_ventas_brutas > 0 else 0.0
        rep_pct = ((v_horas * v_coste_h) / v_ventas_brutas) * 100 if v_ventas_brutas > 0 else 0.0
        v_stock = float(r.get('Stock_Promedio', 0.0))
        sell_through = (v_unids / v_stock) * 100 if v_stock > 0 else 100.0

        df_v_turnos = df_slice[df_slice['Vendedor_ID'] == v_id]
        t_pico = df_v_turnos[df_v_turnos['Trafico_Tienda'] >= p80_traf]
        t_valle = df_v_turnos[df_v_turnos['Trafico_Tienda'] <= p20_traf]
        
        if t_pico['Horas_Trabajadas'].sum() > 0 and t_valle['Horas_Trabajadas'].sum() > 0:
            vph_pico = float(t_pico['Ventas'].sum() / t_pico['Horas_Trabajadas'].sum())
            vph_valle = float(t_valle['Ventas'].sum() / t_valle['Horas_Trabajadas'].sum())
            stress_ratio = (vph_pico / vph_valle) if vph_valle > 0 else 1.0
        else:
            stress_ratio = 1.0

        if 'Tickets_Socio' in r and v_trans > 0:
            tasa_fidelizacion = min(100.0, (float(r['Tickets_Socio']) / v_trans) * 100)
            fid_str = f"{tasa_fidelizacion:.1f}%"
        else:
            tasa_fidelizacion, fid_str = 0.0, "TPV Anónimo"

        if v_aov >= bm_aov and v_upt >= bm_upt: cuadrante, rec = "🌟 ASESOR TOP", "Perfil óptimo consolidado. Asignar como tutor en sala."
        elif v_aov < bm_aov and v_upt < bm_upt: cuadrante, rec = "📦 DESPACHADOR", "Actitud transaccional pasiva. Formación urgente en venta asistida."
        elif v_aov >= bm_aov and v_upt < bm_upt: cuadrante, rec = "🎯 CLOSER (Alto Ticket)", "Gran cierre premium. Capacitar en add-ons para elevar UPT."
        else: cuadrante, rec = "🛒 DISPENSADOR (Cesta Ancha)", "Ofrece complementos pero falla en gama alta. Formar en producto premium."
            
        if tasa_retorno > 8.0: cuadrante, rec = f"⚠️ {cuadrante} (Tóxico)", f"ALERTA DE MARGEN: Retorno del {tasa_retorno:.1f}%. Auditar argumentario."

        turnos_df = df_v_turnos.groupby(df_v_turnos['Fecha'].dt.date).agg(hora_min=('Fecha', lambda x: x.min().hour), hora_max=('Fecha', lambda x: x.max().hour))
        turnos_html = "".join([f"<span class='text-xs'>{f.strftime('%a %d')}: {row['hora_min']:02d}:00 - {row['hora_max']:02d}:00</span><br>" for f, row in turnos_df.iterrows()])

        vendedores_data.append({
            "id": v_id, "upt": round(v_upt, 2), "aov": round(v_aov, 2), 
            "ventas": round(v_ventas_brutas, 2), "ventas_brutas": round(v_ventas_brutas, 2), 
            "venta_neta": round(v_venta_neta, 2), "retorno_pct": round(tasa_retorno, 1), 
            "rep_pct": round(rep_pct, 1), "sell_through": round(sell_through, 1),
            "stress_ratio": round(stress_ratio, 2), "tasa_fidelizacion": fid_str,
            "transacciones": int(v_trans), "horas": round(v_horas, 2), "vph": round(v_vph, 2), 
            "cuadrante": cuadrante, "recomendacion": rec, "turnos": turnos_html
        })
        
        badge_stress = f"<span class='text-emerald-400 font-bold'>[Ratio Estrés: {stress_ratio:.2f} - Crece en agobio]</span>" if stress_ratio > 1.05 else (f"<span class='text-rose-400 font-bold'>[Ratio Estrés: {stress_ratio:.2f} - Colapsa en pico]</span>" if stress_ratio < 0.85 else f"<span class='text-slate-400'>[Ratio Estrés: {stress_ratio:.2f}]</span>")
        alerta_ret_html = f"<span class='text-rose-400 font-bold'>[Retorno: {tasa_retorno:.1f}%]</span>" if tasa_retorno > 8 else f"<span class='text-slate-400'>[Retorno: {tasa_retorno:.1f}%]</span>"

        lineas_dictamen.append(
            f"<div class='border-b border-slate-800/80 pb-3.5 space-y-1'>"
            f"  <div class='flex justify-between text-xs'><span class='text-white font-bold'>• {v_id}</span><span class='text-amber-400 font-mono font-bold'>{cuadrante}</span></div>"
            f"  <p class='text-slate-300 text-xs'>Bruto: <strong class='text-white'>{v_ventas_brutas:,.2f}€</strong> | Neta: <strong class='text-sky-400'>{v_venta_neta:,.2f}€</strong> {alerta_ret_html}. Fidelización: <strong class='text-purple-400'>{fid_str}</strong>.</p>"
            f"  <p class='text-[11px] text-slate-400'>Productividad: {v_vph:.1f} €/h {badge_stress}</p>"
            f"  <p class='text-[11px] text-emerald-400 italic pt-0.5'>Acción Directiva: {rec}</p>"
            f"</div>"
        )
        
    mapa_dias = {0: "1-Lunes", 1: "2-Martes", 2: "3-Miércoles", 3: "4-Jueves", 4: "5-Viernes", 5: "6-Sábado", 6: "7-Domingo"}
    df_slice_cp = df_slice.copy()
    df_slice_cp['Dia_Str']  = df_slice_cp['Fecha'].dt.dayofweek.map(mapa_dias)
    df_slice_cp['Hora_Int'] = df_slice_cp['Fecha'].dt.hour
    df_heat = df_slice_cp.groupby(['Dia_Str', 'Hora_Int']).agg({'Trafico_Tienda': 'mean', 'Horas_Trabajadas': 'mean'}).reset_index()
    df_heat['Ratio'] = (df_heat['Trafico_Tienda'] / df_heat['Horas_Trabajadas'].replace(0, 1)).round(1)
    
    df_eficiencia = df_slice.groupby(df_slice['Fecha'].dt.floor('D')).agg({'Trafico_Tienda': 'sum', 'Horas_Trabajadas': 'sum', 'Coste_Hora': 'first'}).reset_index()
    df_eficiencia['Coste_Laboral'] = df_eficiencia['Horas_Trabajadas'] * df_eficiencia['Coste_Hora']
    df_eficiencia['Fecha_str'] = df_eficiencia['Fecha'].dt.strftime('%b %d %Y')
    
    eficiencia_data = df_eficiencia[['Fecha_str', 'Trafico_Tienda', 'Coste_Laboral']].to_dict(orient='records')
    
    # ===== NUEVOS CAMPOS PARA EL DASHBOARD =====
    # Rotación de stock
    stock_avg = df_slice['Stock_Promedio'].mean() if 'Stock_Promedio' in df_slice.columns else 0
    rotacion_stock = tot_ventas / stock_avg if stock_avg > 0 else 0
    
    # Diferencias vs benchmark
    dif_conv = tasa_conv_global - bm_conv
    dif_aov = aov_global - bm_aov
    # ===========================================
    
    dif_c, dif_a = (tasa_conv_global - bm_conv), (aov_global - bm_aov)
    sc, sa = ("+" if dif_c >= 0 else ""), ("+" if dif_a >= 0 else "")
    cc, ca = ("text-emerald-400" if dif_c >= 0 else "text-rose-400"), ("text-emerald-400" if dif_a >= 0 else "text-rose-400")
    
    html_cobertura = f"<div class='bg-rose-950/30 border border-rose-500/30 p-3.5 rounded-xl space-y-1.5 mt-3'><div class='text-rose-400 font-mono text-xs font-bold flex items-center gap-1.5'><span>🚨</span> DEMOSTRACIÓN DE INFRACOBERTURA EN PICOS</div><p class='text-slate-300 text-xs leading-relaxed'>En franjas de máxima saturación, la sala operó a un ratio de <strong>1 empleado por cada {ratio_staff_trafico:.1f} visitantes</strong> (Estándar {bm_nombre}: 1:{bm_traf_emp}). <span class='text-rose-300'>Hicieron falta exactamente <strong>{deficit_horas_pico:.1f} horas de personal adicionales</strong> en estos tramos para no quebrar la tasa de conversión.</span></p></div>" if deficit_horas_pico > 0.5 else f"<div class='bg-emerald-950/20 border border-emerald-500/20 p-3 rounded-xl mt-3'><p class='text-emerald-400 text-xs font-mono flex items-center gap-1.5'><span>⚖️</span> Cobertura Staff-to-Traffic en picos controlada ({ratio_staff_trafico:.1f} pases/h).</p></div>"

    html_bm = f"<div class='bg-slate-950/90 border border-slate-800 p-3.5 rounded-xl space-y-2'><div class='flex justify-between text-xs font-mono text-sky-400 font-bold tracking-wider uppercase'><span>📊 BENCHMARK: {bm_nombre}</span><span>P50 NACIONAL</span></div><div class='grid grid-cols-2 gap-2 text-xs font-mono'><div class='bg-slate-900/80 p-2 rounded border border-slate-800/80 text-slate-300'>Conversión: <strong class='text-white'>{tasa_conv_global:.1f}%</strong> <span class='{cc} block text-[11px]'>{sc}{dif_c:.1f}% vs INE</span></div><div class='bg-slate-900/80 p-2 rounded border border-slate-800/80 text-slate-300'>Ticket Medio: <strong class='text-white'>{aov_global:.2f}€</strong> <span class='{ca} block text-[11px]'>{sa}{dif_a:.2f}€ vs INE</span></div></div></div>"

    dictamen_completo = f"<div class='space-y-4'><div class='text-xs font-mono text-amber-400 font-bold border-b border-amber-500/20 pb-2 flex justify-between'><span>⚖️ AUDITORÍA DE FUERZA DE VENTAS ({nombre_etiqueta})</span><span class='text-slate-500'>SECTOR: {sector_key.upper()}</span></div>{html_bm}<div class='space-y-3.5'>{''.join(lineas_dictamen)}</div>{html_cobertura}</div>"

    has_secundarias = 'Devoluciones' in df_slice.columns
    return {
        "idle_cost": f"{idle_cost:,.2f}", "cop_cost": f"{cop_cost:,.2f}", "impacto_pct": f"{impacto_pct:.1f}",
        "tot_ventas": f"{tot_ventas:,.2f}", "coste_lab_pct": f"{coste_lab_pct:.1f}", "tasa_conv": f"{tasa_conv_global:.1f}",
        "vph_global": f"{vph_global:.1f}", "aov_global": f"{aov_global:.2f}", "upt_global": f"{upt_global:.2f}",
        "tot_trafico": f"{tot_trafico:,}", "tot_trans": f"{tot_trans:,}",
        "vendedores": vendedores_data, "heatmap": df_heat[['Dia_Str', 'Hora_Int', 'Ratio', 'Trafico_Tienda', 'Horas_Trabajadas']].to_dict(orient='records'), 
        "dictamen": dictamen_completo, "aov_global_num": round(aov_global, 2), "upt_global_num": round(upt_global, 2),
        "eficiencia": eficiencia_data, "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
        "has_secundarias": has_secundarias, "tot_dev": int(df_slice['Devoluciones'].sum()) if has_secundarias else 0, 
        "stock_avg": int(stock_avg), 
        "anti_avg": round(df_slice['Antiguedad_Meses'].mean(), 1) if 'Antiguedad_Meses' in df_slice.columns else 0,
        "sector_nombre": bm_nombre, "ratio_staff_trafico": round(ratio_staff_trafico, 1), "deficit_horas_pico": round(deficit_horas_pico, 1),
        "margen_bruto_usado": round(margen_bruto * 100, 1), "clientes_perdidos_total": round(clientes_perdidos_total, 0),
        # NUEVOS CAMPOS PARA EL DASHBOARD
        "rotacion_stock": round(rotacion_stock, 1),
        "dif_conv": round(dif_conv, 1),
        "dif_aov": round(dif_aov, 2)
    }

def imprimir_auditoria_consola_para_director(df, sector_key="textil"):
    try: 
        df, _ = validar_esquema_datos(df)
    except Exception as e: 
        print(f"❌ Error en esquema: {e}"); return
    res = procesar_periodo(df, "PERIODO COMPLETO", sector_key=sector_key)
    
    print("\n" + "═"*80)
    print(f"📊 AUDITORÍA DE FUERZA DE VENTAS – BENCHMARK: {res['sector_nombre'].upper()}")
    print("═"*80)
    print(f"📅 Período: {res['fecha_inicio']} → {res['fecha_fin']} | 💰 Facturación: {res['tot_ventas']}€")
    print(f"🔄 Conversión: {res['tasa_conv']}% | 🛒 AOV: {res['aov_global']}€ | 📦 UPT: {res['upt_global']}")
    print(f"⚠️ Erosión Total s/ Ingreso: {res['impacto_pct']}% (Ocio: {res['idle_cost']}€ | COP: {res['cop_cost']}€)")
    print(f"📊 Margen Bruto usado: {res.get('margen_bruto_usado', 80)}% | Clientes perdidos: {res.get('clientes_perdidos_total', 0)}")
    if res['deficit_horas_pico'] > 0: print(f"🚨 ALERTA STAFFING: Faltaron {res['deficit_horas_pico']} horas en picos (Ratio 1:{res['ratio_staff_trafico']})")
    
    print("\n" + "─"*80 + "\n👤 DICTAMEN DE VENDEDORES\n" + "─"*80)
    for v in res['vendedores'][:5]:
        print(f" • {v['id']:<22} → {v['cuadrante']:<20} | Bruto: {v['ventas_brutas']:,.2f}€ | REP: {v['rep_pct']}%")
        print(f"   [Productividad: {v['vph']} €/h | Ratio Estrés: {v['stress_ratio']} | Fidelización: {v['tasa_fidelizacion']}]")
        print(f"   Acción: {v['recomendacion']}\n")
    print("═"*80 + "\n")
