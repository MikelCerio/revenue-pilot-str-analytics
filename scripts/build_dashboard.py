"""
build_dashboard.py
==================
Regenera RevenuePilot_Dashboard.html a partir de data/public/.

Contexto
--------
Una version anterior del dashboard llevaba incrustado el P&L real por
edificio (revenue + beneficio neto), que procede del informe de costes
excluido del repositorio. Este script conserva el diseno y la interaccion
de aquella version, pero reconstruye TODA la capa de datos desde el star
schema anonimizado, elimina el bloque de margenes y corrige los textos que
reidentificaban el portfolio.

Cambios respecto a la version de origen:
  - DATA.marginYB eliminado (P&L privado)
  - KPI "Margen Neto" sustituido por "Lead Time medio" (dato publico)
  - capacity tomado de dim_property.inventory_units, no hardcodeado
  - sin referencia geografica ni recuento de apartamentos inventado
  - sin badge "LIVE" (es un HTML estatico)

Uso:
    python scripts/build_dashboard.py [--template RUTA]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "data" / "public"
OUT = ROOT / "outputs" / "RevenuePilot_Dashboard.html"

DEFAULT_TEMPLATE = Path.home() / "Downloads" / "RevenuePilot_Dashboard.html"

# dim_channel tiene 5 claves; el dashboard muestra 3 columnas
CHANNEL_IDX = {1: 0, 2: 1, 3: 2, 4: 2, 5: 2}
CHANNEL_LABELS = ["OTA Principal", "OTA Secundaria", "Directo"]

# Cortes del booking window (dias de antelacion)
LEAD_BUCKETS = [(0, 1), (2, 7), (8, 30), (31, 90), (91, 10**6)]


def log(m: str = "") -> None:
    print(m)


def build_data() -> dict:
    fact = pd.read_parquet(PUBLIC / "fact_reservations.parquet")
    prop = pd.read_csv(PUBLIC / "dim_property.csv")
    rev = pd.read_csv(PUBLIC / "fact_reviews.csv", on_bad_lines="skip")
    mkt = pd.read_csv(PUBLIC / "buildings_vs_market.csv")

    prop = prop.dropna(subset=["property_key"]).sort_values("property_key")
    # property_key 1..5 -> indice 0..4
    pk_to_idx = {int(k): i for i, k in enumerate(prop["property_key"])}
    capacity = [int(v) for v in prop["inventory_units"]]
    labels = [
        s.replace("Edificio ", "Edif. ").replace(" - ", " — ")
        for s in prop["building_name_public"]
    ]

    f = fact[~fact["is_cancelled"].astype(bool)].copy()
    f["year"] = f["date_key_checkin"] // 10000
    f["month"] = (f["date_key_checkin"] // 100) % 100
    f["b"] = f["property_key"].map(pk_to_idx)
    f["c"] = f["channel_key"].map(CHANNEL_IDX)
    f = f.dropna(subset=["b", "c"])

    # ── cube: [year, month, b, c, gross, net, nights, reservas, comision, leadsum]
    g = f.groupby(["year", "month", "b", "c"], as_index=False).agg(
        gross=("revenue_gross", "sum"),
        net=("revenue_net", "sum"),
        nights=("nights", "sum"),
        resv=("reservation_id", "count"),
        comm=("commission", "sum"),
        leadsum=("lead_time_days", "sum"),
    )
    cube = [
        [int(r.year), int(r.month), int(r.b), int(r.c),
         round(float(r.gross)), round(float(r.net)), int(r.nights),
         int(r.resv), round(float(r.comm)), round(float(r.leadsum))]
        for r in g.itertuples()
    ]

    # ── lead: [year, b, c, bucket, count]
    def bucket(d):
        for i, (lo, hi) in enumerate(LEAD_BUCKETS):
            if lo <= d <= hi:
                return i
        return len(LEAD_BUCKETS) - 1

    f["bk"] = f["lead_time_days"].fillna(0).clip(lower=0).map(bucket)
    gl = f.groupby(["year", "b", "c", "bk"], as_index=False).agg(
        n=("reservation_id", "count")
    )
    lead = [
        [int(r.year), int(r.b), int(r.c), int(r.bk), int(r.n)]
        for r in gl.itertuples()
    ]

    # ── reviews
    dash_to_idx = {lbl: i for i, lbl in enumerate(prop["building_name_public"])}

    def norm(s):
        return str(s).replace("—", "-").strip()

    rev["b"] = rev["property"].map(lambda s: dash_to_idx.get(norm(s)))
    rev = rev.dropna(subset=["b"])
    rev["b"] = rev["b"].astype(int)
    rev["year"] = pd.to_datetime(rev["date"], errors="coerce").dt.year

    score_yb: dict = {}
    for (y, b), sub in rev.dropna(subset=["year"]).groupby(["year", "b"]):
        score_yb.setdefault(str(int(y)), {})[str(int(b))] = round(
            float(sub["score"].mean()), 2
        )

    sub_cols = ["Confort", "Limpieza", "Instalaciones y servicios",
                "Ubicación", "Relación calidad-precio", "Personal"]
    review_subs = {
        c: round(float(rev[c].mean()), 2)
        for c in sub_cols if c in rev.columns and rev[c].notna().any()
    }

    topics: list = []
    if "topics_str" in rev.columns:
        cnt: dict = {}
        for s in rev["topics_str"].dropna():
            for tp in str(s).split(","):
                tp = tp.strip()
                if tp:
                    cnt[tp] = cnt.get(tp, 0) + 1
        topics = [[k, v] for k, v in sorted(cnt.items(), key=lambda x: -x[1])[:8]]

    reply_rate = 0.0
    if "has_reply" in rev.columns:
        reply_rate = round(
            float(pd.to_numeric(rev["has_reply"], errors="coerce").fillna(0).mean()), 3
        )

    score_by_b, count_by_b = [], []
    for i in range(len(prop)):
        s = rev[rev["b"] == i]
        score_by_b.append(round(float(s["score"].mean()), 2) if len(s) else None)
        count_by_b.append(int(len(s)))

    # ── mercado (Inside Airbnb, datos publicos)
    b_market = []
    for i in range(len(prop)):
        row = mkt.iloc[i] if i < len(mkt) else None
        b_market.append(
            [round(float(row["our_adr"])), round(float(row["our_occupancy"])),
             float(row["our_score"]), round(float(row["market_median_adr"])),
             round(float(row["vs_market"])), round(float(row["revenue_upside_annual"]))]
            if row is not None else [0, 0, 0, 0, 0, 0]
        )

    market = {
        "adr": int(mkt["market_median_adr"].median()),
        "occ": 47.6,
        "revpar": int(mkt["market_median_adr"].median() * 0.476),
        "adr_p25": int(mkt["market_p25_adr"].median()),
        "adr_p75": int(mkt["market_p75_adr"].median()),
        "occ_note": "Inside Airbnb (datos abiertos)",
    }

    data = {
        "cube": cube,
        "lead": lead,
        "months": ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
        "buildings": labels,
        "capacity": capacity,
        "channels": CHANNEL_LABELS,
        "scoreYB": score_yb,
        "market": market,
        "bMarket": b_market,
        "reviewsTotal": int(len(rev)),
        "reviewSubs": review_subs,
        "topics": topics,
        "reviewReplyRate": reply_rate,
        "reviewScoreByB": score_by_b,
        "reviewCountByB": count_by_b,
    }

    log(f"  cube        : {len(cube)} filas")
    log(f"  lead        : {len(lead)} filas")
    log(f"  capacity    : {capacity} (total {sum(capacity)} unidades)")
    log(f"  reviews     : {data['reviewsTotal']}")
    log(f"  revenue tot : {sum(r[4] for r in cube):,} EUR")
    log("  marginYB    : ELIMINADO (P&L privado)")
    return data


# ── Parches sobre el HTML plantilla ─────────────────────────────────────────
PATCHES: list[tuple[str, str, str]] = [
    # 1. KPI "Margen Neto" -> "Lead Time medio"
    ('<div class="kpi-label">Margen Neto</div>',
     '<div class="kpi-label">Lead Time medio</div>',
     "etiqueta KPI"),
    # 2. Calculo: margen -> lead time
    ("""  // margen neto: desde gastos reales (solo edificios/años con datos de coste)
  let np=0, gr=0, any=false;
  const yrs = (year==='all') ? YEARS : [year];
  yrs.forEach(y=>{
    const mg = DATA.marginYB[y];
    if(!mg) return;
    buildingsInScope().forEach(b=>{ if(mg[b]){ np+=mg[b][0]; gr+=mg[b][1]; any=true; } });
  });
  const margin = any && gr ? np/gr*100 : null;
  const netProfit = any ? np : null;

  return { rev, nights, adr, occ, revpar, score, margin, netProfit };""",
     """  // lead time medio: dias de antelacion, ponderado por numero de reservas
  const leadSum = rows.reduce((s,r)=>s+r[9],0);
  const resvTot = rows.reduce((s,r)=>s+r[7],0);
  const leadAvg = resvTot ? leadSum/resvTot : null;

  return { rev, nights, adr, occ, revpar, score, leadAvg };""",
     "calculo KPI"),
    # 3. Pintado del KPI
    ("""  set('kpi-margin', cur.margin!=null? cur.margin.toFixed(1)+'%' : 's/d');""",
     """  set('kpi-margin', cur.leadAvg!=null? cur.leadAvg.toFixed(1)+' d' : 's/d');""",
     "valor KPI"),
    ("""  set('kpi-margin-sub', cur.netProfit!=null? ('Beneficio: '+fmtMoney(cur.netProfit)) : 'Coste no disponible p/ selección');""",
     """  set('kpi-margin-sub', 'Antelación media de reserva');""",
     "subtexto KPI"),
    # 4. Columna de la tabla por edificio
    ("<th>Margen</th>", "<th>Lead time</th>", "cabecera tabla"),
    ("""    // margen edificio
    let np=0,gr=0,has=false; (year==='all'?YEARS:[year]).forEach(y=>{ const mg=DATA.marginYB[y]; if(mg&&mg[b]){np+=mg[b][0];gr+=mg[b][1];has=true;} });
    const mar= has&&gr? np/gr*100 : null;""",
     """    // lead time por edificio
    const lsum=rb.reduce((s,r)=>s+r[9],0), lres=rb.reduce((s,r)=>s+r[7],0);
    const mar = lres ? lsum/lres : null;""",
     "lead time por edificio"),
    # La celda seguia formateando como porcentaje (heredado del margen)
    ("""<td>${d.mar==null?'<span style="color:var(--muted)">s/d</span>':'~'+d.mar.toFixed(0)+'%'}</td>""",
     """<td>${d.mar==null?'<span style="color:var(--muted)">s/d</span>':d.mar.toFixed(1)+' d'}</td>""",
     "formato celda lead time"),
]

# Sustituciones de texto simples (regex)
TEXT_SUBS = [
    (r"Portfolio STR Analytics\s*·\s*Bilbao,\s*País Vasco",
     "Portfolio STR Analytics"),
    (r"~?\s*44\s*apartamentos", "41 unidades"),
    (r"<span[^>]*>\s*●\s*LIVE\s*</span>", ""),
    (r"●\s*LIVE", "DEMO"),
    # El benchmark usa datos abiertos de Inside Airbnb. Nombrar la ciudad aqui
    # reidentificaria el portfolio, que en el resto del repo va sin ubicacion.
    (r"Mercado STR Bilbao", "Mercado STR comparable"),
    (r"Mercado Bilbao \(mediana\)", "Mercado comparable (mediana)"),
    (r"Mercado Bilbao:", "Mercado comparable:"),
    (r"Mercado Bilbao", "Mercado comparable"),
    (r"Gap ADR vs Mercado Bilbao", "Gap ADR vs mercado comparable"),
    # Fuentes que no acompanan al repo
    (r"Datos AirROI \+ EUSTAT", "Inside Airbnb (datos abiertos)"),
]


def main() -> None:
    tpl = DEFAULT_TEMPLATE
    if "--template" in sys.argv:
        tpl = Path(sys.argv[sys.argv.index("--template") + 1])
    if not tpl.exists():
        sys.exit(f"ERROR: no se encuentra la plantilla {tpl}")

    log("=" * 62)
    log("RECONSTRUCCION DEL DASHBOARD DESDE DATOS PUBLICOS")
    log("=" * 62)
    log(f"Plantilla: {tpl}\n")

    data = build_data()
    html = tpl.read_text(encoding="utf-8")

    # Sustituir el bloque DATA entero
    m = re.search(r"const\s+DATA\s*=\s*\{.*?\};\s*\n", html, re.S)
    if not m:
        sys.exit("ERROR: no se localiza 'const DATA = {...};' en la plantilla")
    nuevo = "const DATA = " + json.dumps(data, ensure_ascii=False) + ";\n"
    html = html[: m.start()] + nuevo + html[m.end():]
    log("\n  bloque DATA sustituido")

    log("\n  --- parches de codigo ---")
    for old, new, label in PATCHES:
        if old in html:
            html = html.replace(old, new)
            log(f"  OK   {label}")
        else:
            log(f"  !!   {label}: patron no encontrado (revisar)")

    log("\n  --- parches de texto ---")
    for pat, rep in TEXT_SUBS:
        html, n = re.subn(pat, rep, html)
        if n:
            log(f"  OK   {pat[:44]}... ({n})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")

    log(f"\n  Escrito: {OUT}  ({OUT.stat().st_size // 1024} KB)")

    # ── Verificacion ───────────────────────────────────────────────────────
    log("\n" + "=" * 62)
    log("VERIFICACION")
    log("=" * 62)
    leaks = []
    for term in ["marginYB", "Beneficio:", "Margen Neto", "Bilbao",
                 "EDIFICIO_D", "EDIFICIO_B", "EDIFICIO_E", "el alojamiento"]:
        if re.search(re.escape(term), html, re.I):
            leaks.append(term)
    # Cifras concretas del P&L privado
    for n in ["412409", "339058", "236767", "189045", "99904"]:
        if n in html:
            leaks.append(f"cifra P&L {n}")
    log(f"  {'FUGAS: ' + ', '.join(leaks) if leaks else 'OK - sin rastro del P&L privado ni del anclaje geografico'}")


if __name__ == "__main__":
    main()
