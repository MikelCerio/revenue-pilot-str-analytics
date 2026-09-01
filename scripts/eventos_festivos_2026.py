# -*- coding: utf-8 -*-
"""
Genera las tablas de EVENTOS y FESTIVOS de Bilbao 2026 para alimentar
el forecast y el modelo de Power BI.

Salidas:
  data/public/dim_event_2026.csv      (eventos con uplift histórico)
  data/public/dim_festivos_2026.csv   (calendario laboral Bilbao 2026 + puentes)

Fuentes (búsqueda web, junio 2026):
  - Bilbao BBK Live: 9-11 jul 2026 (bilbaobbklive.com)
  - Aste Nagusia / Semana Grande: 22-30 ago 2026 (ayto. Bilbao / Kulturklik)
  - Bilbao Night Run Fest: 17 oct 2026 (bilbaonightrun.com)
  - Conciertos San Mamés / BEC: ZETAK 19-20 jun, Aitana 18-19 sep, Dani Martín 3 oct
  - Calendario laboral Bilbao 2026 (euskadi.eus / euskaltel)
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "data" / "public"
OUT.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────────────────
# 1. EVENTOS 2026 (con uplift histórico de ADR observado en el portfolio)
#    El uplift sale del análisis de años anteriores (dim_event original).
# ────────────────────────────────────────────────────────────────
EVENTOS_2026 = [
    # name,            start,        end,          type,            uplift_pct, fuente_demanda
    ("BBK Live",        "2026-07-09", "2026-07-11", "Festival",       29.4, "80+ artistas, Kobetamendi, 20º aniversario"),
    ("Aste Nagusia",    "2026-08-22", "2026-08-30", "Cultural",       24.1, "Semana Grande, 9 días, 100+ conciertos gratis"),
    ("Concierto Aitana","2026-09-18", "2026-09-19", "Concierto",      24.1, "Cuarto Azul World Tour, Bizkaia Arena (BEC)"),
    ("Concierto Dani Martin","2026-10-03","2026-10-03","Concierto",   18.0, "Gira 25 pa' siempre, Bizkaia Arena (BEC)"),
    ("Bilbao Night Run","2026-10-17", "2026-10-17", "Deportivo",       8.0, "18ª ed., salida San Mamés, meta Guggenheim"),
    # Eventos de junio (referencia, justo antes del forecast H2)
    ("Concierto ZETAK", "2026-06-19", "2026-06-20", "Concierto",      18.0, "San Mamés (estadio)"),
]

df_ev = pd.DataFrame(
    EVENTOS_2026,
    columns=["event_name", "start_date", "end_date", "event_type",
             "historical_adr_uplift_pct", "fuente_demanda"],
)
df_ev.insert(0, "event_key", range(1, len(df_ev) + 1))
df_ev["start_date"] = pd.to_datetime(df_ev["start_date"])
df_ev["end_date"] = pd.to_datetime(df_ev["end_date"])
df_ev["year"] = 2026
df_ev["duracion_dias"] = (df_ev["end_date"] - df_ev["start_date"]).dt.days + 1
df_ev["week_iso"] = df_ev["start_date"].dt.isocalendar().week.astype(int)

df_ev.to_csv(OUT / "dim_event_2026.csv", index=False, encoding="utf-8-sig")
print(f"[OK] dim_event_2026.csv  -> {len(df_ev)} eventos")

# ────────────────────────────────────────────────────────────────
# 2. FESTIVOS BILBAO 2026 (calendario laboral oficial)
#    8 nacionales + 4 autonómicos/forales + 2 locales = 14 días
# ────────────────────────────────────────────────────────────────
FESTIVOS_2026 = [
    ("2026-01-01", "Año Nuevo",                 "Nacional"),
    ("2026-01-06", "Epifanía / Reyes",          "Nacional"),
    ("2026-03-19", "San José",                   "Autonómico"),
    ("2026-04-02", "Jueves Santo",              "Autonómico"),
    ("2026-04-03", "Viernes Santo",             "Nacional"),
    ("2026-04-06", "Lunes de Pascua",           "Autonómico"),
    ("2026-05-01", "Día del Trabajo",           "Nacional"),
    ("2026-07-25", "Santiago Apóstol",          "Nacional"),
    ("2026-07-31", "San Ignacio de Loyola",     "Foral (Bizkaia)"),
    ("2026-08-15", "Asunción de la Virgen",     "Nacional"),
    ("2026-08-28", "Semana Grande (Bilbao)",    "Local (Bilbao)"),
    ("2026-10-12", "Fiesta Nacional",            "Nacional"),
    ("2026-12-08", "Inmaculada Concepción",     "Nacional"),
    ("2026-12-25", "Navidad",                    "Nacional"),
]

df_f = pd.DataFrame(FESTIVOS_2026, columns=["date", "festivo", "ambito"])
df_f["date"] = pd.to_datetime(df_f["date"])
dias_es = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
           4: "Viernes", 5: "Sábado", 6: "Domingo"}
df_f["dia_semana"] = df_f["date"].dt.dayofweek.map(dias_es)
df_f["mes"] = df_f["date"].dt.month
df_f["week_iso"] = df_f["date"].dt.isocalendar().week.astype(int)

# Marcar "puente" potencial: festivo en martes (puente lunes) o jueves (puente viernes)
def tipo_puente(dow):
    if dow == 1:   # martes -> puente lunes
        return "Puente (lunes)"
    if dow == 3:   # jueves -> puente viernes
        return "Puente (viernes)"
    if dow == 0:   # lunes -> finde largo
        return "Finde largo"
    if dow == 4:   # viernes -> finde largo
        return "Finde largo"
    return "-"
df_f["oportunidad"] = df_f["date"].dt.dayofweek.map(tipo_puente)

df_f.to_csv(OUT / "dim_festivos_2026.csv", index=False, encoding="utf-8-sig")
print(f"[OK] dim_festivos_2026.csv -> {len(df_f)} festivos")

# Resumen H2 (jul-dic) en consola
print("\n── Festivos relevantes 2º semestre 2026 (demanda) ──")
for _, r in df_f[df_f["mes"] >= 7].iterrows():
    print(f"  {r['date'].strftime('%d-%m-%Y')}  {r['dia_semana']:<10} {r['festivo']:<28} {r['oportunidad']}")
print("\n── Eventos 2º semestre 2026 ──")
for _, r in df_ev[df_ev["start_date"].dt.month >= 7].iterrows():
    print(f"  {r['start_date'].strftime('%d-%m')}–{r['end_date'].strftime('%d-%m')}  "
          f"{r['event_name']:<22} +{r['historical_adr_uplift_pct']}% ADR")
