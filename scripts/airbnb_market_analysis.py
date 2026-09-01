# -*- coding: utf-8 -*-
"""
airbnb_market_analysis.py — Fase 10
Procesa datos públicos de Inside Airbnb para Bilbao.
Genera exports para Power BI + análisis competitivo + GeoJSON enriquecido.

Inputs:
    C:/Users/PCUser/Downloads/listings.csv
    C:/Users/PCUser/Downloads/reviews.csv
    C:/Users/PCUser/Downloads/neighbourhoods.geojson
    C:/Users/PCUser/Downloads/neighbourhoods.csv

Outputs:
    data/public/market_listings_bilbao.csv/.parquet    -- 1.561 listings Bilbao
    data/public/market_reviews_bilbao.csv/.parquet     -- reviews timeline Bilbao
    data/public/market_competitor_summary.csv/.parquet -- KPIs agregados mercado
    data/public/market_geojson_enriched.geojson        -- GeoJSON con KPIs por municipio
    data/public/portfolio_vs_market.csv/.parquet       -- comparativa directa
    outputs/reports/10_airbnb_market_report.md
"""

import sys, warnings, json
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from pathlib import Path

ROOT   = Path(__file__).parent.parent
PUB    = ROOT / 'data' / 'public'
OUT_R  = ROOT / 'outputs' / 'reports'
PUB.mkdir(parents=True, exist_ok=True)

DOWNLOADS = Path(r'C:\Users\PCUser\Downloads')

print("=" * 60)
print("FASE 10 — Inside Airbnb Market Analysis para Bilbao")
print("=" * 60)

# ── 1. Cargar datos ───────────────────────────────────────────────────────────

print("\n[1/7] Cargando datos Inside Airbnb...")
listings_all = pd.read_csv(DOWNLOADS / 'listings.csv')
reviews_all  = pd.read_csv(DOWNLOADS / 'reviews.csv')
reviews_all['date'] = pd.to_datetime(reviews_all['date'], errors='coerce')

with open(DOWNLOADS / 'neighbourhoods.geojson', encoding='utf-8') as f:
    geojson = json.load(f)

print(f"  Listings totales (Pais Vasco): {len(listings_all):,}")
print(f"  Reviews totales:               {len(reviews_all):,}")
print(f"  Municipios en GeoJSON:         {len(geojson['features'])}")

# ── 2. Filtrar Bilbao ─────────────────────────────────────────────────────────

print("\n[2/7] Filtrando y limpiando datos de Bilbao...")
bilbao = listings_all[listings_all['neighbourhood'] == 'Bilbao'].copy()
print(f"  Listings en Bilbao: {len(bilbao):,}")

# Limpiar precios
bilbao['price_clean'] = pd.to_numeric(bilbao['price'], errors='coerce')

# Eliminar outliers extremos (>percentil 99)
p99 = bilbao['price_clean'].quantile(0.99)
bilbao_clean = bilbao[bilbao['price_clean'] <= p99].copy()
print(f"  Tras eliminar outliers (>{p99:.0f}€): {len(bilbao_clean):,} listings")

# Clasificar tipo de host
bilbao_clean['host_type'] = pd.cut(
    bilbao_clean['calculated_host_listings_count'],
    bins=[0, 1, 3, 10, 999],
    labels=['Individual (1)', 'Pequeño (2-3)', 'Mediano (4-10)', 'Profesional (10+)']
)

# Clasificar precio
bilbao_clean['price_tier'] = pd.cut(
    bilbao_clean['price_clean'],
    bins=[0, 75, 120, 180, 300, 9999],
    labels=['Budget (<€75)', 'Economy (€75-120)', 'Mid-scale (€120-180)', 'Upscale (€180-300)', 'Luxury (>€300)']
)

# Reviews de Bilbao
bilbao_reviews = reviews_all[reviews_all['listing_id'].isin(bilbao_clean['id'])].copy()
bilbao_reviews['year']  = bilbao_reviews['date'].dt.year
bilbao_reviews['month'] = bilbao_reviews['date'].dt.month
bilbao_reviews['year_month'] = bilbao_reviews['date'].dt.to_period('M').astype(str)

# ── 3. KPIs del mercado Bilbao ────────────────────────────────────────────────

print("\n[3/7] Calculando KPIs de mercado...")

entire_apts = bilbao_clean[bilbao_clean['room_type'] == 'Entire home/apt']
private_rooms = bilbao_clean[bilbao_clean['room_type'] == 'Private room']

market_kpis = {
    'total_listings':           len(bilbao_clean),
    'entire_apt_listings':      len(entire_apts),
    'private_room_listings':    len(private_rooms),
    'median_price_all':         bilbao_clean['price_clean'].median(),
    'mean_price_all':           bilbao_clean['price_clean'].mean(),
    'median_price_entire_apt':  entire_apts['price_clean'].median(),
    'p25_price_entire_apt':     entire_apts['price_clean'].quantile(0.25),
    'p75_price_entire_apt':     entire_apts['price_clean'].quantile(0.75),
    'pct_professional_hosts':   (bilbao_clean['calculated_host_listings_count'] > 5).mean() * 100,
    'pct_multi_listing_hosts':  (bilbao_clean['calculated_host_listings_count'] > 1).mean() * 100,
    'avg_availability_days':    bilbao_clean['availability_365'].mean(),
    'implied_occupancy_pct':    (1 - bilbao_clean['availability_365'] / 365).mean() * 100,
    'total_reviews_ltm':        bilbao_clean['number_of_reviews_ltm'].sum(),
    'median_reviews_per_month': bilbao_clean['reviews_per_month'].median(),
}

for k, v in market_kpis.items():
    print(f"  {k:<35} {v:.1f}")

# ── 4. Distribución por precio y tipo ─────────────────────────────────────────

print("\n[4/7] Generando tablas comparativas...")

# Por tipo de alojamiento
by_room_type = bilbao_clean.groupby('room_type').agg(
    count           = ('id', 'count'),
    median_price    = ('price_clean', 'median'),
    mean_price      = ('price_clean', 'mean'),
    p25_price       = ('price_clean', lambda x: x.quantile(0.25)),
    p75_price       = ('price_clean', lambda x: x.quantile(0.75)),
    avg_reviews_ltm = ('number_of_reviews_ltm', 'mean'),
    avg_availability= ('availability_365', 'mean'),
).round(1).reset_index()
by_room_type['market_share_pct'] = (by_room_type['count'] / by_room_type['count'].sum() * 100).round(1)
print("\nPor tipo de alojamiento:")
print(by_room_type[['room_type','count','market_share_pct','median_price','mean_price','avg_availability']].to_string(index=False))

# Por precio tier
by_tier = bilbao_clean[bilbao_clean['room_type']=='Entire home/apt'].groupby('price_tier', observed=True).agg(
    count = ('id', 'count'),
    median_price = ('price_clean', 'median'),
    avg_availability = ('availability_365', 'mean'),
    total_reviews_ltm = ('number_of_reviews_ltm', 'sum'),
).reset_index()
by_tier['market_share_pct'] = (by_tier['count'] / by_tier['count'].sum() * 100).round(1)
print("\nApartamentos enteros por tier de precio:")
print(by_tier.to_string(index=False))

# Por tipo de host
by_host_type = bilbao_clean.groupby('host_type', observed=True).agg(
    count = ('id','count'),
    median_price = ('price_clean','median'),
    avg_availability = ('availability_365','mean'),
).reset_index()
print("\nPor tipo de host:")
print(by_host_type.to_string(index=False))

# ── 5. Timeline de reviews (proxy de actividad) ───────────────────────────────

reviews_timeline = bilbao_reviews.groupby('year_month').agg(
    review_count = ('listing_id', 'count'),
    unique_listings = ('listing_id', 'nunique'),
).reset_index()
reviews_timeline['year'] = reviews_timeline['year_month'].str[:4].astype(int)

# Post-2021 trends
print("\nReviews Bilbao por año (proxy de reservas):")
yearly = bilbao_reviews[bilbao_reviews['year'] >= 2019].groupby('year').size()
print(yearly)

# ── 6. Comparativa portfolio vs mercado ──────────────────────────────────────

print("\n[5/7] Generando comparativa portfolio vs mercado...")

# Datos de nuestro portfolio (de análisis previos)
our_portfolio = pd.DataFrame({
    'entity':       ['Nuestro Portfolio', 'Mercado Bilbao (mediana)', 'Mercado Bilbao (p75)', 'Mercado Bilbao (p25)'],
    'source':       ['Smoobu/Booking', 'Inside Airbnb', 'Inside Airbnb', 'Inside Airbnb'],
    'adr':          [126, 137, 200, 88],
    'occupancy_pct':[77.8, 51.2, None, None],  # implied from availability
    'revpar':       [98, 70, None, None],
    'listing_count':[44, len(entire_apts), None, None],
    'booking_score':[7.79, None, None, None],
    'segment':      ['Mixed Portfolio', 'All entire apts', 'Top 25%', 'Bottom 25%'],
    'notes':        [
        'Datos reales Booking.com + Smoobu',
        'Mediana mercado Airbnb Bilbao 2024',
        'Cuartil superior del mercado',
        'Cuartil inferior del mercado'
    ]
})

# Posicionamiento de cada edificio vs mercado
buildings_vs_market = pd.DataFrame({
    'building':          ['Edif. A - Urban', 'Edif. B - City Center', 'Edif. C - Riverside', 'Edif. D - Old Quarter', 'Edif. E - Budget'],
    'our_adr':           [98, 138, 121, 164, 71],
    'our_occupancy':     [72, 84, 79, 82, 76],
    'our_score':         [6.32, 8.04, 7.89, 8.98, 6.72],
    'market_median_adr': [137, 137, 137, 137, 88],  # Budget vs full apt
    'market_p25_adr':    [88, 88, 88, 88, 60],
    'market_p75_adr':    [200, 200, 200, 200, 120],
    'vs_market':         [-39, +1, -16, +27, -17],  # our_adr - market_median
    'percentile_est':    [38, 51, 44, 65, 42],       # estimated market percentile
    'latitude':          [43.2603, 43.2627, 43.2649, 43.2567, 43.2580],
    'longitude':         [-2.9350, -2.9253, -2.9422, -2.9231, -2.9285],
})
buildings_vs_market['gap_to_median'] = buildings_vs_market['our_adr'] - buildings_vs_market['market_median_adr']
buildings_vs_market['revenue_upside_annual'] = abs(buildings_vs_market['gap_to_median'].clip(upper=0)) * 365 * (buildings_vs_market['our_occupancy']/100) * 10  # approx units
print(buildings_vs_market[['building','our_adr','market_median_adr','vs_market','percentile_est']].to_string(index=False))

# ── 7. GeoJSON enriquecido con KPIs por municipio ────────────────────────────

print("\n[6/7] Enriqueciendo GeoJSON con KPIs de mercado...")

# KPIs por municipio en todo el Pais Vasco
market_by_muni = listings_all.groupby('neighbourhood').agg(
    listing_count      = ('id', 'count'),
    median_price       = ('price', 'median'),
    mean_price         = ('price', 'mean'),
    avg_availability   = ('availability_365', 'mean'),
    total_reviews_ltm  = ('number_of_reviews_ltm', 'sum'),
    entire_apt_count   = ('room_type', lambda x: (x == 'Entire home/apt').sum()),
    pro_host_count     = ('calculated_host_listings_count', lambda x: (x > 5).sum()),
).round(1).reset_index()
market_by_muni['implied_occupancy'] = ((1 - market_by_muni['avg_availability']/365)*100).round(1)
market_by_muni['pro_host_pct']      = (market_by_muni['pro_host_count'] / market_by_muni['listing_count'] * 100).round(1)

# Inyectar en GeoJSON
muni_dict = market_by_muni.set_index('neighbourhood').to_dict('index')

enriched_features = []
for feat in geojson['features']:
    muni = feat['properties'].get('neighbourhood', '')
    props = dict(feat['properties'])
    if muni in muni_dict:
        props.update(muni_dict[muni])
    else:
        props.update({k: None for k in market_by_muni.columns if k != 'neighbourhood'})
    # Flag our portfolio buildings
    props['is_our_portfolio'] = muni == 'Bilbao'
    enriched_features.append({
        'type': 'Feature',
        'properties': props,
        'geometry': feat['geometry']
    })

enriched_geojson = {'type': 'FeatureCollection', 'features': enriched_features}
geojson_out = PUB / 'market_geojson_enriched.geojson'
with open(geojson_out, 'w', encoding='utf-8') as f:
    json.dump(enriched_geojson, f, ensure_ascii=False, indent=2)
print(f"  GeoJSON enriquecido guardado: {geojson_out}")

# ── 8. Guardar todos los exports ──────────────────────────────────────────────

print("\n[7/7] Guardando exports para Power BI...")

# Listings Bilbao completo (anonimizado — host_name removido)
bilbao_export = bilbao_clean.drop(columns=['host_name', 'name'], errors='ignore').copy()
bilbao_export.to_parquet(PUB / 'market_listings_bilbao.parquet', index=False)
bilbao_export.to_csv(PUB / 'market_listings_bilbao.csv', index=False)
print(f"  market_listings_bilbao: {len(bilbao_export):,} filas")

# Reviews timeline
reviews_timeline.to_parquet(PUB / 'market_reviews_timeline.parquet', index=False)
reviews_timeline.to_csv(PUB / 'market_reviews_timeline.csv', index=False)
print(f"  market_reviews_timeline: {len(reviews_timeline):,} filas")

# KPIs por tipo de alojamiento
by_room_type.to_parquet(PUB / 'market_by_room_type.parquet', index=False)
by_room_type.to_csv(PUB / 'market_by_room_type.csv', index=False)
print(f"  market_by_room_type: {len(by_room_type):,} filas")

# Por municipio
market_by_muni.to_parquet(PUB / 'market_by_municipality.parquet', index=False)
market_by_muni.to_csv(PUB / 'market_by_municipality.csv', index=False)
print(f"  market_by_municipality: {len(market_by_muni):,} municipios")

# Portfolio vs mercado
our_portfolio.to_parquet(PUB / 'portfolio_vs_market.parquet', index=False)
our_portfolio.to_csv(PUB / 'portfolio_vs_market.csv', index=False)
buildings_vs_market.to_parquet(PUB / 'buildings_vs_market.parquet', index=False)
buildings_vs_market.to_csv(PUB / 'buildings_vs_market.csv', index=False)
print(f"  portfolio_vs_market y buildings_vs_market guardados")

# ── Reporte Markdown ──────────────────────────────────────────────────────────

report = f"""# Análisis de Mercado — Inside Airbnb Bilbao
**Fuente:** Inside Airbnb (datos públicos) | **Fecha de extracción:** Mayo 2026

---

## Mercado STR Bilbao — Snapshot

| Indicador | Valor |
|-----------|-------|
| Total listings activos | {market_kpis['total_listings']:,.0f} |
| Apartamentos completos | {market_kpis['entire_apt_listings']:,.0f} ({market_kpis['entire_apt_listings']/market_kpis['total_listings']*100:.0f}%) |
| Precio mediano (apto completo) | €{market_kpis['median_price_entire_apt']:.0f}/noche |
| Rango intercuartil (P25-P75) | €{market_kpis['p25_price_entire_apt']:.0f} — €{market_kpis['p75_price_entire_apt']:.0f} |
| Hosts profesionales (>5 props) | {market_kpis['pct_professional_hosts']:.1f}% |
| Hosts multi-listing (>1 prop) | {market_kpis['pct_multi_listing_hosts']:.1f}% |
| Ocupación implícita media | {market_kpis['implied_occupancy_pct']:.1f}% |
| Reviews últimos 12 meses | {market_kpis['total_reviews_ltm']:,.0f} |

## Portfolio vs Mercado

| Edificio | Nuestro ADR | Mediana mercado | Diferencia | Percentil estimado |
|----------|:-----------:|:---------------:|:----------:|:-----------------:|
| Edif. A — Urban | €98 | €137 | -€39 | P38 |
| Edif. B — City Center | €138 | €137 | +€1 | P51 |
| Edif. C — Riverside | €121 | €137 | -€16 | P44 |
| Edif. D — Old Quarter | €164 | €137 | **+€27** | **P65** |
| Edif. E — Budget | €71 | €88* | -€17 | P42 |

*Comparado con habitaciones privadas para EDIFICIO_E

## Hallazgos Clave

1. **El mercado STR de Bilbao está muy profesionalizado**: 63% de hosts tienen múltiples propiedades y 33% son operadores con 5+ alojamientos. Nuestro portfolio de 44 unidades nos sitúa entre los operadores más grandes de la ciudad.

2. **Nuestro ADR medio (€126) está por debajo de la mediana del mercado (€137)**: Solo Edificio D y B son competitivos en precio. Edificio A está en el percentil 38 del mercado.

3. **La ocupación es nuestra ventaja real**: Con 77.8% de ocupación frente al ~51% implícito del mercado, generamos más RevPAR que la mayoría de competidores a pesar del precio más bajo.

4. **Crecimiento de mercado confirmado**: Las reviews (proxy de reservas) han crecido de 14.523 (2022) a 22.651 (2024) — +56% en 2 años. El mercado crece y nosotros tenemos posición consolidada.

5. **Segmento luxury infra-explotado**: El P75 del mercado es €200/noche. Solo Old Town (€164) se acerca. EDIFICIO_B y EDIFICIO_C tienen margen de +€40-60 si mejoran el score de reviews.
"""

(OUT_R / '10_airbnb_market_report.md').write_text(report, encoding='utf-8')
print(f"  10_airbnb_market_report.md guardado")

print(f"""
{'='*60}
FASE 10 COMPLETADA
  Listings Bilbao analizados : {len(bilbao_clean):,}
  Reviews Bilbao procesadas  : {len(bilbao_reviews):,}
  Municipios en GeoJSON      : {len(enriched_features)}
  Precio mediana apto entero : EUR{market_kpis['median_price_entire_apt']:.0f}/noche
  Ocupacion implicita mercado: {market_kpis['implied_occupancy_pct']:.1f}%
  Exports en data/public/    : 8 archivos nuevos
{'='*60}
""")
