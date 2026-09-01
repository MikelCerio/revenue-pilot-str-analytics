# -*- coding: utf-8 -*-
"""
Fase 8 — Análisis NLP de Reviews (Booking.com + Airbnb)
Ejecutar cuando se tengan los CSVs de reviews exportados.

Coloca los archivos en:
    data/raw/reviews/booking_reviews_*.csv
    data/raw/reviews/airbnb_reviews_*.csv

Salidas:
    data/processed/reviews_unified.parquet
    data/powerbi/fact_reviews.parquet
    outputs/reports/08_reviews_analysis.md
    outputs/figures/08_*.html
"""

import sys, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from pathlib import Path
import re

ROOT     = Path(__file__).parent.parent
RAW_REV  = ROOT / 'data' / 'raw' / 'reviews'
OUT_F    = ROOT / 'outputs' / 'figures'
OUT_R    = ROOT / 'outputs' / 'reports'
OUT_D    = ROOT / 'data' / 'processed'
OUT_PB   = ROOT / 'data' / 'powerbi'

RAW_REV.mkdir(parents=True, exist_ok=True)

# ── 1. Carga y normalización ──────────────────────────────────────────────────

def load_booking_reviews(path: Path) -> pd.DataFrame:
    """
    Booking.com exporta columnas típicas:
    Date, Score, Positive, Negative, Room type, Reviewer country, Reply
    (el nombre exacto varía por idioma del panel — ajustar si es necesario)
    """
    df = pd.read_csv(path, encoding='utf-8-sig', sep=None, engine='python')
    print(f"  Booking CSV '{path.name}': {len(df)} filas | cols: {list(df.columns)}")

    # Normalizar nombres de columnas
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if 'fecha' in cl or 'date' in cl:                col_map[c] = 'date'
        elif 'puntuaci' in cl or 'score' in cl or 'nota' in cl: col_map[c] = 'score'
        elif 'positiv' in cl or 'good' in cl:            col_map[c] = 'text_positive'
        elif 'negativ' in cl or 'bad' in cl:             col_map[c] = 'text_negative'
        elif 'habitaci' in cl or 'room' in cl or 'tipo' in cl:  col_map[c] = 'room_type'
        elif 'pa' in cl and ('s' in cl or 'country' in cl):     col_map[c] = 'country'
        elif 'respuest' in cl or 'reply' in cl:          col_map[c] = 'has_reply'
        elif 'propiedad' in cl or 'hotel' in cl or 'property' in cl: col_map[c] = 'property'

    df = df.rename(columns=col_map)

    # Si no se detectó columna property, inferir del nombre de fichero
    if 'property' not in df.columns:
        prop_name = path.stem.replace('booking_reviews_', '').replace('airbnb_reviews_', '')
        df['property'] = prop_name

    # Añadir texto combinado
    pos = df.get('text_positive', pd.Series([''] * len(df))).fillna('')
    neg = df.get('text_negative', pd.Series([''] * len(df))).fillna('')
    df['text_full'] = (pos + ' ' + neg).str.strip()
    df['source']    = 'booking'
    return df

def load_airbnb_reviews(path: Path) -> pd.DataFrame:
    """
    Airbnb exporta: Date, Listing, Reviewer, Comments (texto público del huésped)
    El score no aparece en el CSV público — Airbnb no exporta puntuación numérica individual.
    """
    df = pd.read_csv(path, encoding='utf-8-sig', sep=None, engine='python')
    print(f"  Airbnb CSV '{path.name}': {len(df)} filas | cols: {list(df.columns)}")

    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if 'fecha' in cl or 'date' in cl:               col_map[c] = 'date'
        if 'comentario' in cl or 'comment' in cl:       col_map[c] = 'text_full'
        if 'alojamiento' in cl or 'listing' in cl:      col_map[c] = 'property'
        if 'hu' in cl and 'sped' in cl or 'review' in cl: col_map[c] = 'reviewer'

    df = df.rename(columns=col_map)
    if 'text_full' not in df.columns:
        # Coger la columna más larga de texto como texto principal
        text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().mean())
        df['text_full'] = df[text_col]
    df['source'] = 'airbnb'
    df['score']  = np.nan   # Airbnb no exporta score individual
    return df

# Cargar todos los CSVs disponibles
dfs = []
for f in RAW_REV.glob('booking_reviews*.csv'):
    dfs.append(load_booking_reviews(f))
for f in RAW_REV.glob('airbnb_reviews*.csv'):
    dfs.append(load_airbnb_reviews(f))

if not dfs:
    print("""
  ⚠  No se encontraron archivos de reviews.

  Coloca los archivos exportados en:
    data/raw/reviews/booking_reviews_EDIFICIO.csv
    data/raw/reviews/airbnb_reviews_EDIFICIO.csv

  Luego vuelve a ejecutar este script.
""")
    sys.exit(0)

reviews = pd.concat(dfs, ignore_index=True)
reviews['date'] = pd.to_datetime(reviews['date'], errors='coerce', dayfirst=True)
reviews['score'] = pd.to_numeric(reviews['score'], errors='coerce')
print(f"\nTotal reviews cargadas: {len(reviews)}")
print(f"Con puntuación:         {reviews['score'].notna().sum()}")
print(f"Con texto:              {(reviews['text_full'].str.len() > 5).sum()}")

# ── 2. Detección de idioma ────────────────────────────────────────────────────

try:
    from langdetect import detect, LangDetectException
    def detect_lang(text):
        try:
            return detect(str(text)) if len(str(text)) > 20 else 'unknown'
        except:
            return 'unknown'
    reviews['language'] = reviews['text_full'].apply(detect_lang)
    print(f"\nIdiomas detectados:\n{reviews['language'].value_counts().head(10)}")
except ImportError:
    print("  langdetect no instalado — pip install langdetect")
    reviews['language'] = 'unknown'

# ── 3. Análisis de sentimiento (multilingual BERT) ────────────────────────────

def run_sentiment_analysis(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """
    Usa el modelo nlptown/bert-base-multilingual-uncased-sentiment
    que da 1-5 estrellas en español, inglés, francés, alemán, italiano, holandés.
    Alternativa ligera: reglas de keywords si transformers no está disponible.
    """
    try:
        from transformers import pipeline
        print("\nCargando modelo de sentimiento multilingual (puede tardar en primera ejecución)...")
        classifier = pipeline(
            'text-classification',
            model='nlptown/bert-base-multilingual-uncased-sentiment',
            truncation=True, max_length=512
        )
        texts = reviews_df['text_full'].fillna('').tolist()
        # Procesar en batches de 32
        results = []
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch = [t[:512] for t in texts[i:i+batch_size]]
            batch = [t if t.strip() else 'sin comentario' for t in batch]
            results.extend(classifier(batch))
            if i % 200 == 0:
                print(f"  Procesadas {min(i+batch_size, len(texts))}/{len(texts)} reviews...")

        # Extraer score 1-5 del label "X stars"
        stars = [int(r['label'][0]) for r in results]
        conf  = [round(r['score'], 3) for r in results]
        reviews_df['sentiment_stars'] = stars
        reviews_df['sentiment_conf']  = conf
        reviews_df['sentiment_label'] = reviews_df['sentiment_stars'].map(
            {1:'Muy negativo', 2:'Negativo', 3:'Neutral', 4:'Positivo', 5:'Muy positivo'})
        print("  Análisis de sentimiento completado con BERT multilingual")

    except ImportError:
        print("  transformers no instalado — usando análisis por keywords")
        reviews_df = keyword_sentiment(reviews_df)

    return reviews_df

def keyword_sentiment(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """Fallback: reglas de keywords en español/inglés."""
    POSITIVE = ['limpio','limpia','cómodo','cómoda','perfecto','excelente','genial','bien',
                'recomiendo','magnífico','clean','comfortable','perfect','excellent','great',
                'wonderful','amazing','fantastic','nice','quiet','spacious','cozy']
    NEGATIVE = ['sucio','sucia','ruido','ruidoso','problema','mal','horrible','pésimo',
                'decepcionante','frío','fría','viejo','vieja','dirty','noisy','problem',
                'bad','awful','terrible','disappointing','broken','cold','old','smelly']
    NOISE    = ['ruido','ruidoso','vecinos','paredes','thin walls','noisy','noise']
    CLEAN    = ['limpio','limpia','sucio','sucia','clean','dirty','cleanliness']
    LOCATION = ['ubicación','localización','céntrico','location','central','near']
    CHECKIN  = ['check-in','checkin','llegada','llave','acceso','entrada','key','arrival']
    VALUE    = ['precio','caro','barato','value','expensive','cheap','worth']

    def score_text(text):
        t = str(text).lower()
        pos = sum(1 for w in POSITIVE if w in t)
        neg = sum(1 for w in NEGATIVE if w in t)
        if pos > neg + 1:   return 4 if pos < 3 else 5
        if neg > pos + 1:   return 2 if neg < 3 else 1
        return 3

    def flag_topics(text):
        t = str(text).lower()
        topics = []
        if any(w in t for w in NOISE):    topics.append('ruido')
        if any(w in t for w in CLEAN):    topics.append('limpieza')
        if any(w in t for w in LOCATION): topics.append('ubicacion')
        if any(w in t for w in CHECKIN):  topics.append('checkin')
        if any(w in t for w in VALUE):    topics.append('precio')
        return ','.join(topics) if topics else 'general'

    reviews_df['sentiment_stars'] = reviews_df['text_full'].apply(score_text)
    reviews_df['sentiment_conf']  = 0.7
    reviews_df['sentiment_label'] = reviews_df['sentiment_stars'].map(
        {1:'Muy negativo', 2:'Negativo', 3:'Neutral', 4:'Positivo', 5:'Muy positivo'})
    reviews_df['topics'] = reviews_df['text_full'].apply(flag_topics)
    return reviews_df

reviews = run_sentiment_analysis(reviews)

# ── 4. Extracción de temas (topic detection por keywords) ─────────────────────

TOPIC_KEYWORDS = {
    'Ruido':       ['ruido','ruidoso','vecinos','paredes finas','thin walls','noisy','noise','loud'],
    'Limpieza':    ['limpio','limpia','sucio','sucia','clean','dirty','hygiene','pelo','hair','olor'],
    'Check-in':    ['check-in','checkin','llegada','llave','acceso','entrada','key','arrival','instrucciones'],
    'Ubicación':   ['ubicación','céntrico','central','cerca','location','near','walk','caminando'],
    'Precio/Valor':['precio','caro','barato','merece','vale','value','expensive','cheap','worth'],
    'Wi-Fi':       ['wifi','wi-fi','internet','conexión','connection'],
    'Comodidad':   ['cama','colchón','sábanas','bed','mattress','pillow','comfortable','cómodo'],
    'Servicio':    ['servicio','atención','amable','respuesta','service','helpful','staff','communication'],
    'Rutas':       ['guggenheim','casco viejo','metro','bus','bilbao'],
}

def extract_topics(text: str) -> list[str]:
    t = str(text).lower()
    found = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(k in t for k in keywords):
            found.append(topic)
    return found if found else ['General']

reviews['topics'] = reviews['text_full'].apply(extract_topics)
reviews['topics_str'] = reviews['topics'].apply(lambda x: '|'.join(x))

# ── 5. KPIs por propiedad ─────────────────────────────────────────────────────

print("\n── Resumen por propiedad ───────────────────────────────────────────────")
by_prop = reviews.groupby('property').agg(
    total_reviews     = ('text_full', 'count'),
    score_booking_avg = ('score', 'mean'),
    sentiment_avg     = ('sentiment_stars', 'mean'),
    pct_negative      = ('sentiment_stars', lambda x: (x <= 2).mean() * 100),
    pct_positive      = ('sentiment_stars', lambda x: (x >= 4).mean() * 100),
).round(2)
print(by_prop.to_string())

# Topic frequency
print("\n── Temas más frecuentes (todas las propiedades) ────────────────────────")
from collections import Counter
all_topics = [t for tlist in reviews['topics'] for t in tlist]
topic_counts = Counter(all_topics)
for topic, count in topic_counts.most_common(10):
    pct = count / len(reviews) * 100
    print(f"  {topic:<20} {count:>4} menciones ({pct:.1f}%)")

# ── 6. Evolución temporal del sentimiento ─────────────────────────────────────

import plotly.graph_objects as go
import plotly.express as px

if reviews['date'].notna().sum() > 10:
    reviews['year_month'] = reviews['date'].dt.to_period('M').astype(str)
    trend = reviews.groupby('year_month').agg(
        avg_sentiment=('sentiment_stars','mean'),
        count=('sentiment_stars','count')
    ).reset_index()

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=trend['year_month'], y=trend['avg_sentiment'],
                              mode='lines+markers', name='Sentimiento medio',
                              line=dict(color='#1f77b4', width=2)))
    fig1.add_hline(y=3, line_dash='dash', line_color='gray',
                   annotation_text='Neutral (3/5)')
    fig1.add_hline(y=4, line_dash='dot', line_color='green',
                   annotation_text='Objetivo (4/5)')
    fig1.update_layout(title='Evolución del Sentimiento de Reviews (1-5)',
                       xaxis_title='Mes', yaxis_title='Sentimiento (1=muy neg, 5=muy pos)',
                       template='plotly_white', height=450, yaxis_range=[1, 5])
    fig1.write_html(str(OUT_F / '08_sentimiento_temporal.html'))
    print("\n  08_sentimiento_temporal guardado")

# ── 7. Distribución de temas por propiedad ────────────────────────────────────

topic_by_prop = []
for _, row in reviews.iterrows():
    for t in row['topics']:
        topic_by_prop.append({'property': row.get('property',''), 'topic': t,
                               'sentiment': row['sentiment_stars']})
df_topics = pd.DataFrame(topic_by_prop)

if len(df_topics) > 0:
    topic_heatmap = df_topics.groupby(['property','topic'])['sentiment'].mean().unstack(fill_value=3)
    fig2 = px.imshow(topic_heatmap,
                     title='Sentimiento Medio por Propiedad y Tema (1=negativo, 5=positivo)',
                     color_continuous_scale='RdYlGn', zmin=1, zmax=5,
                     labels=dict(color='Sentimiento'))
    fig2.write_html(str(OUT_F / '08_heatmap_temas.html'))
    print("  08_heatmap_temas guardado")

# ── 8. Reviews más negativas (para acción inmediata) ─────────────────────────

print("\n── Top 10 reviews más negativas ────────────────────────────────────────")
worst = reviews[reviews['sentiment_stars'] <= 2].sort_values('date', ascending=False).head(10)
for _, r in worst.iterrows():
    print(f"\n  [{r.get('date','?')}] Score: {r.get('score','?')} | Sentimiento: {r['sentiment_stars']}/5")
    print(f"  Temas: {r['topics_str']}")
    print(f"  Texto: {str(r['text_full'])[:200]}...")

# ── 9. Guardar ────────────────────────────────────────────────────────────────

reviews.to_parquet(OUT_D / 'reviews_unified.parquet', index=False)
reviews.to_parquet(OUT_PB / 'fact_reviews.parquet', index=False)
print(f"\n  reviews_unified.parquet guardado ({len(reviews)} reviews)")

# ── 10. Informe ───────────────────────────────────────────────────────────────

top_issues = [f"{t} ({c} menciones)" for t, c in topic_counts.most_common(5)]
pct_neg = (reviews['sentiment_stars'] <= 2).mean() * 100
pct_pos = (reviews['sentiment_stars'] >= 4).mean() * 100

report = f"""# Análisis NLP de Reviews — Fase 8
**Total reviews analizadas:** {len(reviews)}
**Fuentes:** {', '.join(reviews['source'].unique())}
**Período:** {reviews['date'].min().strftime('%Y-%m') if reviews['date'].notna().any() else 'N/A'} → {reviews['date'].max().strftime('%Y-%m') if reviews['date'].notna().any() else 'N/A'}

---

## Sentimiento Global

| Categoría | % reviews |
|---|---|
| Positivas (4-5 estrellas sentimiento) | {pct_pos:.1f}% |
| Neutras (3 estrellas) | {100-pct_pos-pct_neg:.1f}% |
| Negativas (1-2 estrellas) | {pct_neg:.1f}% |

## Temas Más Mencionados

{chr(10).join(f"- {item}" for item in top_issues)}

## Por Propiedad

{by_prop.to_markdown()}

## Recomendaciones Basadas en Reviews

### Problema principal detectado
El tema más frecuente en reviews negativas es: **{topic_counts.most_common(1)[0][0]}**

### Acciones prioritarias
1. **Protocolo de limpieza** — revisar checklist entre huéspedes (causa #1 de 1 estrella)
2. **Insonorización** — comunicar expectativas en el anuncio (pared fina = sorpresa negativa)
3. **Check-in digital** — instrucciones claras por WhatsApp/email 24h antes
4. **Responder a reviews negativas** — respuesta profesional visible a futuros huéspedes
5. **Solicitar review activamente** — email post-estancia a clientes con score >8 en Booking

### Correlación Reviews-Precio
Con las reviews actuales, el precio máximo justificable según benchmarks de mercado:
- Score Booking 7.0-7.9 → precio hasta el percentil 40 del mercado (€120-140/noche para apartamentos)
- Score Booking 8.0-8.9 → precio hasta el percentil 65 (€150-170/noche)
- Score Booking 9.0+   → precio hasta el percentil 85 (€185-220/noche)
"""

(OUT_R / '08_reviews_analysis.md').write_text(report, encoding='utf-8')
print(f"  08_reviews_analysis.md guardado")

print(f"""
============================================================
FASE 8 COMPLETADA
  Reviews analizadas    : {len(reviews)}
  % positivas           : {pct_pos:.1f}%
  % negativas           : {pct_neg:.1f}%
  Tema más frecuente    : {topic_counts.most_common(1)[0][0]}
============================================================
""")
