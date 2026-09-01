# -*- coding: utf-8 -*-
"""
FORECAST 2026 (2º semestre) — Demanda + Precio recomendado por edificio y semana.

Usa los 3 modelos LightGBM ya entrenados:
  - model_A_demand.pkl  -> ocupación semanal esperada (%)
  - model_C_price.pkl   -> ADR recomendado (€/noche)

Lags reales: calcula ocupación y ADR de 2025 por semana ISO a partir de
fact_reservations (no usa valores planos). Aplica eventos y festivos 2026.

Salidas:
  outputs/forecast_2026_H2.csv
  outputs/Forecast_RevenuePilot_2026.xlsx  (4 hojas, listo para presentar)
  data/public/fact_forecast_2026.csv       (para importar en Power BI)
"""
import sys, json
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

ROOT   = Path(__file__).parent.parent
PUB    = ROOT / "data" / "public"
MODELS = ROOT / "data" / "processed" / "models"
OUT    = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

# ── Inventario (noches disponibles/semana = unidades × 7) ───────────────
INV = {"EDIFICIO_A": 2, "EDIFICIO_B": 9, "EDIFICIO_C": 9, "EDIFICIO_D": 7, "EDIFICIO_E": 14}
NOMBRE_PUB = {
    "EDIFICIO_A": "Edificio A – Urban District",
    "EDIFICIO_B": "Edificio B – City Center",
    "EDIFICIO_C": "Edificio C – Riverside",
    "EDIFICIO_D": "Edificio D – Old Quarter",
    "EDIFICIO_E": "Edificio E – Budget Inn",
}
KEY2CODE = {1: "EDIFICIO_A", 2: "EDIFICIO_B", 3: "EDIFICIO_C", 4: "EDIFICIO_D", 5: "EDIFICIO_E"}

def cyclic(val, max_val):
    return np.sin(2 * np.pi * val / max_val), np.cos(2 * np.pi * val / max_val)

# ────────────────────────────────────────────────────────────────
# 1. LAGS REALES 2025: ocupación % y ADR medio por edificio × semana ISO
# ────────────────────────────────────────────────────────────────
print("Calculando lags reales de 2025 desde fact_reservations...")
res = pd.read_parquet(PUB / "fact_reservations.parquet")
res = res[~res["is_cancelled"].astype(bool)].copy()
res["building"] = res["property_key"].map(KEY2CODE)
res["checkin"] = pd.to_datetime(res["date_key_checkin"].astype(str), format="%Y%m%d")
res["checkout"] = pd.to_datetime(res["date_key_checkout"].astype(str), format="%Y%m%d")

# --- ADR medio por edificio × semana ISO de check-in (año 2025) ---
res25 = res[res["checkin"].dt.year == 2025].copy()
res25["wk"] = res25["checkin"].dt.isocalendar().week.astype(int)
adr_lag = (res25.groupby(["building", "wk"])["adr"].mean().round(2)).to_dict()
adr_bld_mean = res25.groupby("building")["adr"].mean().round(2).to_dict()

# --- Ocupación: expandir reservas 2025 a noches y contar por semana ISO ---
exp = res[(res["checkout"] > "2025-01-01") & (res["checkin"] < "2026-01-01")].copy()
noches = []
for b, ci, co in zip(exp["building"], exp["checkin"], exp["checkout"]):
    if pd.isna(b) or pd.isna(ci) or pd.isna(co):
        continue
    for d in pd.date_range(ci, co - pd.Timedelta(days=1), freq="D"):
        if d.year == 2025:
            noches.append((b, d.isocalendar().week))
df_n = pd.DataFrame(noches, columns=["building", "wk"])
occ_nights = df_n.groupby(["building", "wk"]).size().to_dict()

occ_lag = {}
for (b, wk), n in occ_nights.items():
    avail = INV.get(b, 1) * 7
    occ_lag[(b, wk)] = round(min(n / avail * 100, 100), 1)
occ_bld_mean = {b: round(np.mean([v for (bb, _), v in occ_lag.items() if bb == b]), 1)
                for b in INV}
print(f"  -> ocupación media 2025 por edificio: {occ_bld_mean}")

# ────────────────────────────────────────────────────────────────
# 2. EVENTOS y FESTIVOS 2026
# ────────────────────────────────────────────────────────────────
ev = pd.read_csv(PUB / "dim_event_2026.csv", parse_dates=["start_date", "end_date"])
fes = pd.read_csv(PUB / "dim_festivos_2026.csv", parse_dates=["date"])

def evento_en_semana(monday, sunday):
    hit = ev[(ev["start_date"] <= sunday) & (ev["end_date"] >= monday)]
    if hit.empty:
        return 0, "", 0.0
    r = hit.iloc[0]
    return 1, r["event_name"], float(r["historical_adr_uplift_pct"])

def festivo_en_semana(monday, sunday):
    hit = fes[(fes["date"] >= monday) & (fes["date"] <= sunday)]
    if hit.empty:
        return 0, ""
    return 1, "; ".join(hit["festivo"].tolist())

# ────────────────────────────────────────────────────────────────
# 3. CARGAR MODELOS
# ────────────────────────────────────────────────────────────────
model_A = joblib.load(MODELS / "model_A_demand.pkl")
model_C = joblib.load(MODELS / "model_C_price.pkl")
le_bld  = joblib.load(MODELS / "le_building.pkl")
feat_A  = joblib.load(MODELS / "features_A.pkl")
feat_C  = joblib.load(MODELS / "features_C.pkl")

# ────────────────────────────────────────────────────────────────
# 4. GENERAR FORECAST: semanas Jul–Dic 2026
# ────────────────────────────────────────────────────────────────
# Lunes desde la semana del 1-jul-2026 hasta fin de año
first_monday = pd.Timestamp("2026-06-29")   # lunes ISO de la semana que contiene 1-jul
mondays = pd.date_range(first_monday, "2026-12-28", freq="W-MON")

YEAR = 2026
rows = []
prev_occ = {b: occ_bld_mean[b] for b in INV}   # seed occ_lag1

for monday in mondays:
    sunday = monday + pd.Timedelta(days=6)
    iso = monday.isocalendar()
    wk = int(iso.week)
    month = monday.month
    wk_sin, wk_cos = cyclic(wk, 52)
    mo_sin, mo_cos = cyclic(month, 12)
    is_event, ev_name, uplift = evento_en_semana(monday, sunday)
    is_fest, fest_name = festivo_en_semana(monday, sunday)
    # tratar festivo "puente/finde largo" como driver de demanda extra
    is_demand_event = 1 if (is_event or is_fest) else 0

    for b in INV:
        bld_enc = le_bld.transform([b])[0]
        avail = INV[b] * 7
        o_l52 = occ_lag.get((b, wk), occ_bld_mean[b])
        a_l52 = adr_lag.get((b, wk), adr_bld_mean[b])

        # --- Modelo A: ocupación esperada ---
        rowA = {
            "building_enc": bld_enc, "wk_sin": wk_sin, "wk_cos": wk_cos,
            "mo_sin": mo_sin, "mo_cos": mo_cos, "is_event": is_demand_event,
            "year": YEAR, "occ_lag1": prev_occ[b], "occ_lag52": o_l52,
            "adr_lag52": a_l52, "avail": avail,
        }
        XA = pd.DataFrame([rowA])[feat_A]
        pred_occ = float(np.clip(model_A.predict(XA)[0], 0, 100))
        prev_occ[b] = pred_occ

        # --- Modelo C: ADR recomendado (base midweek y finde) ---
        def precio(is_wkend):
            rowC = {
                "building_enc": bld_enc, "wk_sin": wk_sin, "wk_cos": wk_cos,
                "mo_sin": mo_sin, "mo_cos": mo_cos, "is_wkend": is_wkend,
                "is_event": is_demand_event, "lt_days": 21, "nights_c": 2,
                "pred_occ": pred_occ, "occ_lag52": o_l52, "adr_lag52": a_l52,
                "year": YEAR,
            }
            XC = pd.DataFrame([rowC])[feat_C]
            return float(np.clip(model_C.predict(XC)[0], 20, 1000))

        adr_base = precio(0)
        adr_finde = precio(1)

        signal = ("Alta — subir precio" if pred_occ >= 80 else
                  "Media" if pred_occ >= 50 else
                  "Baja — descuento last-minute")
        ajustes = []
        if is_event:
            ajustes.append(f"Evento: {ev_name} (+{uplift:.0f}% hist.)")
        if is_fest:
            ajustes.append(f"Festivo: {fest_name}")
        if pred_occ >= 80:
            ajustes.append("Ocupación alta esperada")

        rows.append({
            "edificio": b,
            "nombre": NOMBRE_PUB[b],
            "year": YEAR,
            "week_iso": wk,
            "semana": f"{monday.strftime('%d-%b')} a {sunday.strftime('%d-%b')}",
            "mes": monday.strftime("%B").capitalize(),
            "mes_num": month,
            "ocupacion_pred_pct": round(pred_occ, 1),
            "adr_recomendado": round(adr_base, 2),
            "adr_finde": round(adr_finde, 2),
            "rango_min": round(adr_base * 0.90, 2),
            "rango_max": round(adr_base * 1.10, 2),
            "revpar_estimado": round(pred_occ / 100 * adr_base, 2),
            "is_evento": bool(is_event),
            "evento": ev_name,
            "is_festivo": bool(is_fest),
            "festivo": fest_name,
            "senal_demanda": signal,
            "ajustes": " | ".join(ajustes) if ajustes else "Sin ajustes",
        })

fc = pd.DataFrame(rows)
fc.to_csv(OUT / "forecast_2026_H2.csv", index=False, encoding="utf-8-sig")
fc.to_csv(PUB / "fact_forecast_2026.csv", index=False, encoding="utf-8-sig")
print(f"\n[OK] forecast_2026_H2.csv -> {len(fc)} filas (semanas × edificios)")

# ────────────────────────────────────────────────────────────────
# 5. RESUMEN MENSUAL POR EDIFICIO (presentación)
# ────────────────────────────────────────────────────────────────
dias_mes = {7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
resumen = (fc.groupby(["edificio", "nombre", "mes_num", "mes"])
             .agg(ocupacion_media=("ocupacion_pred_pct", "mean"),
                  adr_medio=("adr_recomendado", "mean"),
                  revpar_medio=("revpar_estimado", "mean"))
             .reset_index())
resumen["ingresos_estimados"] = (
    resumen["revpar_medio"]
    * resumen["edificio"].map(INV)
    * resumen["mes_num"].map(dias_mes)
).round(0)
for c in ["ocupacion_media", "adr_medio", "revpar_medio"]:
    resumen[c] = resumen[c].round(1)
resumen = resumen.sort_values(["edificio", "mes_num"])

# ────────────────────────────────────────────────────────────────
# 6. EXCEL MULTI-HOJA listo para presentar
# ────────────────────────────────────────────────────────────────
xlsx = OUT / "Forecast_RevenuePilot_2026.xlsx"
with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
    fc.to_excel(w, sheet_name="Forecast semanal", index=False)
    resumen.to_excel(w, sheet_name="Resumen mensual", index=False)
    ev.to_excel(w, sheet_name="Eventos 2026", index=False)
    fes.to_excel(w, sheet_name="Festivos 2026", index=False)
print(f"[OK] {xlsx.name} (4 hojas)")

# Consola: top semanas por RevPAR
print("\n── Top 8 semanas por RevPAR estimado (oportunidad de pricing) ──")
top = fc.sort_values("revpar_estimado", ascending=False).head(8)
for _, r in top.iterrows():
    print(f"  {r['edificio']:<10} {r['semana']:<18} occ {r['ocupacion_pred_pct']:>5}%  "
          f"ADR {r['adr_recomendado']:>6}€  RevPAR {r['revpar_estimado']:>6}€  "
          f"{r['evento'] or r['festivo']}")

print("\n── Ingresos estimados 2º semestre por edificio ──")
ing = resumen.groupby("edificio")["ingresos_estimados"].sum().sort_values(ascending=False)
for b, v in ing.items():
    print(f"  {NOMBRE_PUB[b]:<32} {v:>12,.0f} €")
print(f"  {'TOTAL PORTFOLIO H2-2026':<32} {ing.sum():>12,.0f} €")
