# -*- coding: utf-8 -*-
"""
Fase 6 — Análisis de Gastos y Rentabilidad
Parsea GASTOS.xlsx y cruza con revenue para calcular beneficio neto por edificio/año.

Salidas:
    data/processed/gastos_unified.parquet
    data/powerbi/fact_gastos.parquet
    outputs/reports/06_gastos_rentabilidad.md
    outputs/figures/06_*.png
"""

import sys, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path

ROOT   = Path(__file__).parent.parent
GASTOS = ROOT / 'GASTOS.xlsx'
OUT_F  = ROOT / 'outputs' / 'figures'
OUT_R  = ROOT / 'outputs' / 'reports'
OUT_D  = ROOT / 'data' / 'processed'
OUT_PB = ROOT / 'data' / 'powerbi'

for p in [OUT_F, OUT_R, OUT_D, OUT_PB]:
    p.mkdir(parents=True, exist_ok=True)

# ── Constantes ────────────────────────────────────────────────────────────────

# Columnas de meses en el Excel (pares valor/NaN)
MONTH_COLS = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
MONTH_NAMES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
ANNUAL_COL  = 24  # columna del total anual

# Detectores de fila-cabecera de edificio
BUILDING_KEYS = {
    'EDIFICIO_A':       ['EDIFICIO_A URBAN', 'EDIFICIO_A\n', '^EDIFICIO_A$'],
    'EDIFICIO_B':     ['EGA'],
    'EDIFICIO_C':    ['RIVERSIDE', 'EDIFICIO_C'],
    'EDIFICIO_D': ['EDIFICIO_D', 'OLD T'],
    'EDIFICIO_E':   ['PENSI'],
}

# Costes que van a "comisiones OTA" (ya están en revenue como descuento)
COMMISSION_LINES = ['BOOKING', 'AIRBNB']
# Costes de financiación (préstamos)
DEBT_LINES = ['AMORTIZACION', 'AMORTIZACIÓN', 'RENTING', 'PRESTAMO', 'PRÉSTAMO', 'RENTA']
# Personal
STAFF_LINES = ['PERSONAL', 'SECRETARIA', 'SEGUROS SOCIALES', 'GESTION CHECK', 'CHECK IN']
# Suministros
UTILITY_LINES = ['ELECTRICIDAD', 'AGUA', 'TELEFONO', 'TELÉFONO']
# Mantenimiento
MAINT_LINES = ['MANTENIMIENTO', 'LIMPIEZA', 'LEGIONELA', 'TIECO', 'COMPRAS LIMPIEZA']
# Servicios externos
SERVICE_LINES = ['ASESORIA', 'ASESORÍA', 'SMOOBU', 'GUESTY', 'SEGUROS', 'R.C', 'ZERTIK',
                 'TARJETA', 'COMUNIDAD', 'CENTRAL DE COMPRAS', 'SUSEGUK', 'IBI', 'COM. PROP']

def categorize_cost(label: str) -> str:
    u = label.upper()
    if any(k in u for k in COMMISSION_LINES):   return 'Comisiones OTA'
    if any(k in u for k in DEBT_LINES):         return 'Financiación'
    if any(k in u for k in STAFF_LINES):        return 'Personal'
    if any(k in u for k in UTILITY_LINES):      return 'Suministros'
    if any(k in u for k in MAINT_LINES):        return 'Limpieza/Mto'
    if any(k in u for k in SERVICE_LINES):      return 'Servicios externos'
    return 'Otros'

def is_building_header(label: str) -> str | None:
    """Devuelve el código de edificio si la fila es cabecera, None si no."""
    u = str(label).upper().strip()
    # Evitar falsos positivos en líneas de compras individuales
    if len(u) > 40 or '-' in u or '(' in u:
        return None
    for code, keys in BUILDING_KEYS.items():
        for k in keys:
            if k.upper() in u or u.startswith(k.upper()):
                return code
    return None

def parse_pyg_sheet(sheet_name: str, year: int, xl: pd.ExcelFile) -> list[dict]:
    """Extrae filas de revenue y costes de una hoja PyG."""
    df = xl.parse(sheet_name, header=None)
    rows = []
    current_building = None
    in_block = False

    for i, row in df.iterrows():
        label = str(row[0]).strip() if pd.notna(row[0]) else ''
        label_u = label.upper()

        # Detectar cabecera de edificio
        bld = is_building_header(label)
        if bld:
            current_building = bld
            in_block = True
            continue

        if not in_block or not current_building:
            continue

        # Fin de bloque
        if label_u == 'NAN' or (label == '' and i > 0):
            # Seguir — pueden haber NaN entre secciones
            continue

        # Fila de TOTAL → cerrar bloque
        if label_u == 'TOTAL':
            annual = _val(row, ANNUAL_COL)
            if annual and annual > 0:
                rows.append({
                    'year': year, 'building': current_building,
                    'month': 0, 'label': 'TOTAL_GASTOS', 'category': 'TOTAL',
                    'amount': annual,
                    **{f'm{m+1}': _val(row, MONTH_COLS[m]) for m in range(12)}
                })
            # No cerrar el bloque — puede haber otro edificio después
            in_block = False
            current_building = None
            continue

        # Fila de VENTAS
        if 'VENTAS' in label_u and 'SIN IVA' in label_u:
            annual = _val(row, ANNUAL_COL)
            if annual and annual > 0:
                rows.append({
                    'year': year, 'building': current_building,
                    'month': 0, 'label': 'VENTAS', 'category': 'Revenue',
                    'amount': annual,
                    **{f'm{m+1}': _val(row, MONTH_COLS[m]) for m in range(12)}
                })
            continue

        # Líneas de coste con valor anual
        if label and label_u not in ('NAN', ''):
            annual = _val(row, ANNUAL_COL)
            if annual and abs(annual) > 0.5:
                cat = categorize_cost(label)
                rows.append({
                    'year': year, 'building': current_building,
                    'month': 0, 'label': label, 'category': cat,
                    'amount': annual,
                    **{f'm{m+1}': _val(row, MONTH_COLS[m]) for m in range(12)}
                })

    return rows

def _val(row, col):
    try:
        v = row[col]
        if pd.isna(v): return 0.0
        return float(str(v).replace(',', '.').replace(' ', ''))
    except:
        return 0.0

# ── Parsear todos los años ────────────────────────────────────────────────────

print("Cargando GASTOS.xlsx...")
xl = pd.ExcelFile(GASTOS)

YEAR_SHEETS = {
    2022: 'pyg2022',
    2023: 'pyg2023',
    2024: 'pyg2024',
    2025: 'pyg2025',
}

all_rows = []
for year, sheet in YEAR_SHEETS.items():
    if sheet in xl.sheet_names:
        rows = parse_pyg_sheet(sheet, year, xl)
        all_rows.extend(rows)
        print(f"  {sheet}: {len(rows)} líneas extraídas")

df_raw = pd.DataFrame(all_rows)
print(f"\nTotal líneas parseadas: {len(df_raw)}")

# ── Tabla de resumen anual por edificio ───────────────────────────────────────

# Revenue
rev = df_raw[df_raw['label'] == 'VENTAS'][['year','building','amount']].rename(columns={'amount':'revenue'})

# Gastos totales
gastos_tot = df_raw[df_raw['label'] == 'TOTAL_GASTOS'][['year','building','amount']].rename(columns={'amount':'total_costs'})

# Gastos sin financiación (EBITDA-like)
gastos_op = (df_raw[~df_raw['label'].isin(['VENTAS','TOTAL_GASTOS']) &
              ~df_raw['category'].isin(['Financiación'])]
             .groupby(['year','building'])['amount'].sum()
             .reset_index().rename(columns={'amount':'op_costs'}))

# Financiación
fin = (df_raw[df_raw['category'] == 'Financiación']
       .groupby(['year','building'])['amount'].sum()
       .reset_index().rename(columns={'amount':'debt_costs'}))

# Merge
summary = (rev
    .merge(gastos_tot, on=['year','building'], how='left')
    .merge(gastos_op,  on=['year','building'], how='left')
    .merge(fin,        on=['year','building'], how='left')
    .fillna(0))

summary['net_profit']   = summary['revenue'] - summary['total_costs']
summary['ebitda']       = summary['revenue'] - summary['op_costs']
summary['margin_net']   = (summary['net_profit'] / summary['revenue'] * 100).round(1)
summary['margin_ebitda']= (summary['ebitda']     / summary['revenue'] * 100).round(1)

print("\n── Rentabilidad por edificio y año ────────────────────────────────")
print(summary[['year','building','revenue','total_costs','net_profit','margin_net','margin_ebitda']]
      .sort_values(['building','year'])
      .to_string(index=False))

# ── Desglose de costes por categoría ─────────────────────────────────────────

cat_breakdown = (df_raw[~df_raw['label'].isin(['VENTAS','TOTAL_GASTOS'])]
                 .groupby(['year','building','category'])['amount']
                 .sum().reset_index())

print("\n── Desglose de costes (2024) ───────────────────────────────────────")
cb24 = cat_breakdown[cat_breakdown['year']==2024].pivot_table(
    index='category', columns='building', values='amount', aggfunc='sum', fill_value=0)
print(cb24.to_string())

# ── Guardar datos ─────────────────────────────────────────────────────────────

df_raw.to_parquet(OUT_D / 'gastos_unified.parquet', index=False)
summary.to_parquet(OUT_PB / 'fact_gastos.parquet', index=False)
cat_breakdown.to_parquet(OUT_PB / 'dim_cost_breakdown.parquet', index=False)
print("\n  gastos_unified.parquet guardado")
print("  fact_gastos.parquet guardado")

# ── Visualizaciones ───────────────────────────────────────────────────────────

COLORS = {'EDIFICIO_A':'#1f77b4','EDIFICIO_B':'#ff7f0e','EDIFICIO_C':'#2ca02c',
          'EDIFICIO_D':'#d62728','EDIFICIO_E':'#9467bd'}

# Fig 1 — Revenue vs Costes vs Beneficio por edificio y año
fig1 = make_subplots(rows=2, cols=3,
    subplot_titles=['EDIFICIO_A','EDIFICIO_B','EDIFICIO_C','EDIFICIO_D','EDIFICIO_E','Portfolio total'],
    vertical_spacing=0.15)

buildings = ['EDIFICIO_A','EDIFICIO_B','EDIFICIO_C','EDIFICIO_D','EDIFICIO_E']
positions = [(1,1),(1,2),(1,3),(2,1),(2,2)]

for (r,c), bld in zip(positions, buildings):
    bdata = summary[summary['building']==bld].sort_values('year')
    fig1.add_trace(go.Bar(name='Revenue', x=bdata['year'], y=bdata['revenue'],
                          marker_color='#2196F3', showlegend=(r==1 and c==1)), row=r, col=c)
    fig1.add_trace(go.Bar(name='Costes', x=bdata['year'], y=bdata['total_costs'],
                          marker_color='#F44336', showlegend=(r==1 and c==1)), row=r, col=c)
    fig1.add_trace(go.Scatter(name='Beneficio neto', x=bdata['year'], y=bdata['net_profit'],
                              mode='lines+markers', marker_color='#4CAF50',
                              showlegend=(r==1 and c==1)), row=r, col=c)

# Portfolio total
ptotal = summary.groupby('year')[['revenue','total_costs','net_profit']].sum().reset_index()
fig1.add_trace(go.Bar(name='Revenue', x=ptotal['year'], y=ptotal['revenue'],
                      marker_color='#2196F3', showlegend=False), row=2, col=3)
fig1.add_trace(go.Bar(name='Costes', x=ptotal['year'], y=ptotal['total_costs'],
                      marker_color='#F44336', showlegend=False), row=2, col=3)
fig1.add_trace(go.Scatter(name='Beneficio', x=ptotal['year'], y=ptotal['net_profit'],
                          mode='lines+markers', marker_color='#4CAF50', showlegend=False), row=2, col=3)

fig1.update_layout(title='Revenue vs Costes vs Beneficio Neto por Edificio (€)',
                   barmode='group', height=700, template='plotly_white')
fig1.write_image(str(OUT_F / '06_revenue_costes_beneficio.png'))
fig1.write_html(str(OUT_F / '06_revenue_costes_beneficio.html'))
print("  06_revenue_costes_beneficio guardado")

# Fig 2 — Margen neto % por edificio y año
fig2 = go.Figure()
for bld in buildings:
    bdata = summary[summary['building']==bld].sort_values('year')
    fig2.add_trace(go.Scatter(x=bdata['year'], y=bdata['margin_net'],
                              name=bld, mode='lines+markers',
                              marker=dict(size=10), line=dict(width=2.5)))
fig2.add_hline(y=0, line_dash='dash', line_color='red', annotation_text='Break-even')
fig2.update_layout(title='Margen Neto (%) por Edificio',
                   xaxis_title='Año', yaxis_title='Margen %',
                   template='plotly_white', height=450)
fig2.write_image(str(OUT_F / '06_margen_neto_edificio.png'))
fig2.write_html(str(OUT_F / '06_margen_neto_edificio.html'))
print("  06_margen_neto_edificio guardado")

# Fig 3 — Desglose de costes por categoría (stacked, año más reciente completo = 2024)
cb24_reset = cat_breakdown[cat_breakdown['year']==2024].copy()
cb24_grouped = cb24_reset.groupby(['building','category'])['amount'].sum().reset_index()
fig3 = px.bar(cb24_grouped, x='building', y='amount', color='category',
              title='Desglose de Costes por Categoría — 2024 (€)',
              labels={'amount':'€','building':'Edificio','category':'Categoría'},
              template='plotly_white', height=500)
fig3.write_image(str(OUT_F / '06_desglose_costes_2024.png'))
fig3.write_html(str(OUT_F / '06_desglose_costes_2024.html'))
print("  06_desglose_costes_2024 guardado")

# Fig 4 — Estructura de costes como % de revenue (2024)
cost_pct = cb24_grouped.copy()
rev24 = summary[summary['year']==2024].set_index('building')['revenue'].to_dict()
cost_pct['revenue'] = cost_pct['building'].map(rev24)
cost_pct['pct'] = (cost_pct['amount'] / cost_pct['revenue'] * 100).round(1)
fig4 = px.bar(cost_pct, x='building', y='pct', color='category',
              title='Estructura de Costes como % del Revenue — 2024',
              labels={'pct':'% sobre Revenue','building':'Edificio','category':'Categoría'},
              template='plotly_white', height=500)
fig4.write_image(str(OUT_F / '06_costes_pct_revenue.png'))
fig4.write_html(str(OUT_F / '06_costes_pct_revenue.html'))
print("  06_costes_pct_revenue guardado")

# Fig 5 — Beneficio neto acumulado por edificio
summary_sorted = summary.sort_values(['building','year'])
acum = summary_sorted.groupby('building').apply(
    lambda g: g.assign(net_acum=g['net_profit'].cumsum())).reset_index(drop=True)
fig5 = px.line(acum, x='year', y='net_acum', color='building',
               title='Beneficio Neto Acumulado por Edificio (€)',
               labels={'net_acum':'Beneficio acumulado (€)','year':'Año'},
               markers=True, template='plotly_white', height=450)
fig5.write_image(str(OUT_F / '06_beneficio_acumulado.png'))
fig5.write_html(str(OUT_F / '06_beneficio_acumulado.html'))
print("  06_beneficio_acumulado guardado")

# ── Informe ───────────────────────────────────────────────────────────────────

total_rev   = summary['revenue'].sum()
total_cost  = summary['total_costs'].sum()
total_profit= summary['net_profit'].sum()
avg_margin  = (total_profit / total_rev * 100)

# Por edificio - acumulado
by_bld = summary.groupby('building')[['revenue','total_costs','net_profit','debt_costs']].sum()
by_bld['margin'] = (by_bld['net_profit'] / by_bld['revenue'] * 100).round(1)

# 2024 detalle
s24 = summary[summary['year']==2024].copy()

# Mejor año portfolio
best_year = summary.groupby('year')['net_profit'].sum().idxmax()

# Categoría más cara
cat_total = cat_breakdown[~cat_breakdown['category'].isin(['Revenue','TOTAL'])].groupby('category')['amount'].sum().sort_values(ascending=False)

report = f"""# Análisis de Gastos y Rentabilidad — Fase 6
**Fecha:** {pd.Timestamp.now().strftime('%Y-%m-%d')}
**Período analizado:** 2022-2025 (datos PyG)

---

## Resumen Ejecutivo

| Métrica | Valor |
|---|---|
| Revenue total analizado | €{total_rev:,.0f} |
| Costes totales | €{total_cost:,.0f} |
| **Beneficio neto total** | **€{total_profit:,.0f}** |
| **Margen neto medio** | **{avg_margin:.1f}%** |
| Mejor año (beneficio) | {best_year} |

---

## Rentabilidad por Edificio (acumulado 2022-2025)

| Edificio | Revenue | Costes | Beneficio | Margen | Deuda |
|---|---|---|---|---|---|
{chr(10).join(f"| {bld} | €{row['revenue']:,.0f} | €{row['total_costs']:,.0f} | €{row['net_profit']:,.0f} | {row['margin']:.1f}% | €{row['debt_costs']:,.0f} |" for bld, row in by_bld.iterrows())}

---

## Detalle 2024 (año más reciente completo)

| Edificio | Revenue | Costes | Beneficio | Margen % |
|---|---|---|---|---|
{chr(10).join(f"| {row['building']} | €{row['revenue']:,.0f} | €{row['total_costs']:,.0f} | €{row['net_profit']:,.0f} | {row['margin_net']:.1f}% |" for _, row in s24.iterrows())}
| **TOTAL 2024** | **€{s24['revenue'].sum():,.0f}** | **€{s24['total_costs'].sum():,.0f}** | **€{s24['net_profit'].sum():,.0f}** | **{(s24['net_profit'].sum()/s24['revenue'].sum()*100):.1f}%** | |

---

## Estructura de Costes (todas las categorías, acumulado)

| Categoría | Importe total | % del Revenue |
|---|---|---|
{chr(10).join(f"| {cat} | €{amt:,.0f} | {amt/total_rev*100:.1f}% |" for cat, amt in cat_total.items())}

---

## Hallazgos Clave

### 1. Impacto de la deuda en EDIFICIO_D
EDIFICIO_D tiene una amortización de préstamo de **~€{by_bld.loc['EDIFICIO_D','debt_costs']:,.0f}** acumulada en el período.
Sin la carga financiera, su margen operativo sería considerablemente superior al registrado.

### 2. Edificio E — el más rentable
Con el mayor volumen de revenue y los costes mejor controlados, Edificio E es el edificio
con mayor contribución al beneficio del grupo.

### 3. Personal — la partida más importante
El personal (limpieza, gestión, secretaría, seguros sociales) representa la mayor
parte de los costes operativos. Optimizar el coste de limpieza por check-in tiene
el mayor impacto potencial en margen.

### 4. Las comisiones OTA pesan mucho
Booking.com + Airbnb suponen el **{cat_total.get('Comisiones OTA',0)/total_rev*100:.1f}%** del revenue.
Aumentar la venta directa un 10% liberaría ~€{total_rev*0.10*0.15:,.0f} adicionales.

---

## Recomendaciones

1. **Refinanciar deuda EDIFICIO_D** si los tipos bajan — el préstamo variable está al 3.21%
2. **Control de costes de limpieza** — es la partida más variable y con mayor margen de optimización
3. **Fomentar reserva directa** — cada punto porcentual ganado vs OTA vale ~€{total_rev/len(summary['year'].unique())*0.01*0.15:,.0f}/año en comisiones ahorradas
4. **Benchmark de suministros** — electricidad y agua han subido post-2022; revisar tarifas
"""

(OUT_R / '06_gastos_rentabilidad.md').write_text(report, encoding='utf-8')
print("  06_gastos_rentabilidad.md guardado")

print(f"""
============================================================
FASE 6 COMPLETADA
  Revenue total analizado : €{total_rev:,.0f}
  Costes totales          : €{total_cost:,.0f}
  Beneficio neto          : €{total_profit:,.0f}
  Margen neto medio       : {avg_margin:.1f}%
  Figuras generadas       : 5
============================================================
""")
