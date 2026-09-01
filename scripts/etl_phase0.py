# -*- coding: utf-8 -*-
"""
ETL Fase 0 — Unificación de reservas Bilbao (2019-2026)
Fuentes: XLS Booking (2019-2024), Booking Statements CSVs (2021-2025), Smoobu (2025-2026)
Salida:  data/processed/reservas_unified.parquet
         outputs/reports/00_data_quality.md
"""

import sys, os, glob, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from pathlib import Path

# ── Rutas ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RAW  = ROOT  # los archivos crudos están en la raíz del proyecto
OUT_DATA    = ROOT / 'data' / 'processed'
OUT_REPORTS = ROOT / 'outputs' / 'reports'
OUT_DATA.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

# Inventario de edificios por palabra clave en apartment_name
BUILDING_MAP = {
    'EDIFICIO_A': 'EDIFICIO_A', 'BU EDIFICIO_A': 'EDIFICIO_A',
    'Edificio A': 'EDIFICIO_A',
    'Edificio B': 'EDIFICIO_B',
    'Edificio C': 'EDIFICIO_C',
    'OLD TOWN': 'EDIFICIO_D',
    'EDIFICIO_B': 'EDIFICIO_B', 'EDIFICIO_B': 'EDIFICIO_B',
    'AMSTERDAM': 'EDIFICIO_B', 'BERLIN': 'EDIFICIO_B', 'CHICAGO': 'EDIFICIO_B',
    'DUBLIN': 'EDIFICIO_B', 'HELSINKI': 'EDIFICIO_B', 'LISBOA': 'EDIFICIO_B',
    'MONACO': 'EDIFICIO_B', 'OSLO': 'EDIFICIO_B', 'PRAGA': 'EDIFICIO_B',
    'EDIFICIO_C': 'EDIFICIO_C', 'ALEJANDRA': 'EDIFICIO_C', 'BRUNO': 'EDIFICIO_C',
    'CELESTE': 'EDIFICIO_C', 'DARIO': 'EDIFICIO_C', 'ELENA': 'EDIFICIO_C',
    'FIDEL': 'EDIFICIO_C', 'GLORIA': 'EDIFICIO_C', 'HUGUET': 'EDIFICIO_C',
    'HUGHET': 'EDIFICIO_C', 'OLIVIA': 'EDIFICIO_C',
    'EDIFICIO_D': 'EDIFICIO_D', 'AMBOTO': 'EDIFICIO_D', 'ARRAIZ': 'EDIFICIO_D',
    'ARTXANDA': 'EDIFICIO_D', 'COBETAS': 'EDIFICIO_D', 'GANETA': 'EDIFICIO_D',
    'MUGARRA': 'EDIFICIO_D', 'PAGASARRI': 'EDIFICIO_D',
    'EDIFICIO_E': 'EDIFICIO_E', 'EDIFICIO_E': 'EDIFICIO_E', 'EDIFICIO_E': 'EDIFICIO_E',
    'GARAJE': 'GARAJE',
}

def infer_building(name: str) -> str:
    if pd.isna(name):
        return 'UNKNOWN'
    name_up = str(name).upper()
    for kw, building in BUILDING_MAP.items():
        if kw in name_up:
            return building
    return 'UNKNOWN'


# ── FLAGS de calidad ──────────────────────────────────────────────────────────
FLAGS = {
    'NO_APARTMENT': 'sin_apartamento',
    'NO_BOOKING_DATE': 'sin_fecha_reserva',
    'NEGATIVE_NIGHTS': 'noches_negativas',
    'ZERO_PRICE_ACTIVE': 'precio_cero_activa',
    'DUPLICATE_XREF': 'duplicado_entre_fuentes',
    'NO_COUNTRY': 'sin_pais',
}


# ═══════════════════════════════════════════════════════════════════════════════
# FUENTE 1 — XLS Booking (2019–2024)
# ═══════════════════════════════════════════════════════════════════════════════
def load_xls_booking() -> pd.DataFrame:
    """Carga y normaliza los 6 archivos XLS de Booking.com (exportados desde Smoobu)."""
    xls_files = sorted(glob.glob(str(RAW / 'Reservas_*.xls')))
    print(f"  XLS files encontrados: {len(xls_files)}")

    frames = []
    for f in xls_files:
        try:
            df = pd.read_excel(f)
            df['_file'] = Path(f).name
            frames.append(df)
        except Exception as e:
            print(f"  WARN: no se pudo leer {f}: {e}")

    if not frames:
        return pd.DataFrame()

    raw = pd.concat(frames, ignore_index=True)

    # Normalizar columnas (pueden tener caracteres raros por encoding)
    col_map = {}
    for c in raw.columns:
        cu = str(c).upper().strip()
        if 'NMERO DE RESERVA' in cu or 'MERO DE RESERVA' in cu or cu == 'NÚMERO DE RESERVA':
            col_map[c] = 'reservation_id'
        elif 'NOMBRE DEL ALOJAMIENTO' in cu:
            col_map[c] = 'apartment_name'
        elif 'LLEGADA' in cu:
            col_map[c] = 'check_in_raw'
        elif 'SALIDA' in cu:
            col_map[c] = 'check_out_raw'
        elif 'FECHA DE RESERVA' in cu:
            col_map[c] = 'booking_date_raw'
        elif 'ESTADO' in cu:
            col_map[c] = 'status_raw'
        elif 'IMPORTE TOTAL' in cu:
            col_map[c] = 'gross_amount'
        elif 'COMISI' in cu and 'N' in cu:
            col_map[c] = 'commission_amount'
        elif 'DIVISA' in cu:
            col_map[c] = 'currency'
        elif 'TITULAR' in cu:
            col_map[c] = 'guest_name'

    raw = raw.rename(columns=col_map)

    # Parsear fechas (formato: "27 de mayo de 2019")
    MESES = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }

    def parse_es_date(val):
        if pd.isna(val):
            return pd.NaT
        s = str(val).lower().strip()
        for mes_es, mes_num in MESES.items():
            s = s.replace(f' de {mes_es} de ', f'-{mes_num}-')
            s = s.replace(f' de {mes_es}', f'-{mes_num}')
        try:
            return pd.to_datetime(s, dayfirst=True, errors='coerce')
        except Exception:
            return pd.NaT

    raw['check_in']     = raw['check_in_raw'].apply(parse_es_date)
    raw['check_out']    = raw['check_out_raw'].apply(parse_es_date)
    raw['booking_date'] = raw.get('booking_date_raw', pd.Series([pd.NaT]*len(raw))).apply(parse_es_date)

    # Normalizar reservation_id
    raw['reservation_id'] = pd.to_numeric(raw['reservation_id'], errors='coerce').astype('Int64')

    # Status
    raw['status']    = raw.get('status_raw', pd.Series([''] * len(raw))).fillna('').str.upper().str.strip()
    raw['cancelled'] = raw['status'].isin(['CANCELLED', 'CANCELADO', 'CANCELADA']).astype(bool)

    # Importe y comisión
    raw['gross_amount']       = pd.to_numeric(raw.get('gross_amount'), errors='coerce')
    raw['commission_amount']  = pd.to_numeric(raw.get('commission_amount'), errors='coerce')
    raw['commission_pct']     = np.where(
        raw['gross_amount'] > 0,
        (raw['commission_amount'] / raw['gross_amount'] * 100).round(2),
        np.nan
    )
    raw['net_amount'] = raw['gross_amount'] - raw['commission_amount'].fillna(0)

    out = pd.DataFrame({
        'reservation_id':    raw['reservation_id'],
        'source':            'xls_booking',
        'channel':           'Booking.com',
        'apartment_name':    raw.get('apartment_name', pd.Series([np.nan]*len(raw))),
        'apartment_id':      pd.NA,
        'check_in':          raw['check_in'],
        'check_out':         raw['check_out'],
        'booking_date':      raw['booking_date'],
        'nights':            (raw['check_out'] - raw['check_in']).dt.days,
        'adults':            pd.NA,
        'children':          pd.NA,
        'gross_amount':      raw['gross_amount'],
        'commission_pct':    raw['commission_pct'],
        'commission_amount': raw['commission_amount'],
        'net_amount':        raw['net_amount'],
        'currency':          raw.get('currency', pd.Series(['EUR']*len(raw))).fillna('EUR'),
        'status':            raw['status'],
        'cancelled':         raw['cancelled'],
        'country':           pd.NA,
        'guest_name':        raw.get('guest_name', pd.Series([np.nan]*len(raw))),
    })

    print(f"  XLS: {len(out)} filas cargadas, rango {out['check_in'].min().date()} → {out['check_in'].max().date()}")
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# FUENTE 2 — Booking Statements CSVs (2021–2025)
# ═══════════════════════════════════════════════════════════════════════════════
def load_booking_statements() -> pd.DataFrame:
    """Carga los 41 CSVs de estados de cuenta de Booking.com. Aporta Country."""
    csv_files = sorted(glob.glob(str(RAW / 'reservation_statements_overview_*.csv')))
    print(f"  Booking Statements files: {len(csv_files)}")

    frames = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, encoding='utf-8', on_bad_lines='skip')
            frames.append(df)
        except Exception:
            try:
                df = pd.read_csv(f, encoding='latin-1', on_bad_lines='skip')
                frames.append(df)
            except Exception as e:
                print(f"  WARN: {Path(f).name}: {e}")

    if not frames:
        return pd.DataFrame()

    raw = pd.concat(frames, ignore_index=True)

    # Columnas esperadas: Reservation number, Booked on, Arrival, Departure,
    # Final amount, Commission amount, Commission %, Status, Currency, Country,
    # Property name, Persons, Room nights

    raw['reservation_id']    = pd.to_numeric(raw.get('Reservation number'), errors='coerce').astype('Int64')
    raw['check_in']          = pd.to_datetime(raw.get('Arrival'), errors='coerce')
    raw['check_out']         = pd.to_datetime(raw.get('Departure'), errors='coerce')
    raw['booking_date']      = pd.to_datetime(raw.get('Booked on'), errors='coerce')
    raw['gross_amount']      = pd.to_numeric(raw.get('Original amount'), errors='coerce')
    raw['final_amount']      = pd.to_numeric(raw.get('Final amount'), errors='coerce')
    raw['commission_amount'] = pd.to_numeric(raw.get('Commission amount'), errors='coerce')
    raw['commission_pct']    = pd.to_numeric(raw.get('Commission %'), errors='coerce')
    raw['net_amount']        = raw['final_amount'] - raw['commission_amount'].fillna(0)
    raw['status_raw']        = raw.get('Status', pd.Series(['']*len(raw))).fillna('').str.upper().str.strip()
    raw['cancelled']         = raw['status_raw'].isin(['CANCELLED', 'CANCEL']).astype(bool)
    raw['country']           = raw.get('Country', pd.Series([np.nan]*len(raw)))
    raw['apartment_name']    = raw.get('Property name', pd.Series([np.nan]*len(raw)))
    raw['adults']            = pd.to_numeric(raw.get('Persons'), errors='coerce').astype('Int64')
    raw['nights']            = pd.to_numeric(raw.get('Room nights'), errors='coerce').astype('Int64')

    # Donde nights=0 (canceladas sin estancia) calculamos desde fechas
    mask = raw['nights'].isna() | (raw['nights'] == 0)
    raw.loc[mask, 'nights'] = (raw.loc[mask, 'check_out'] - raw.loc[mask, 'check_in']).dt.days

    out = pd.DataFrame({
        'reservation_id':    raw['reservation_id'],
        'source':            'statements_booking',
        'channel':           'Booking.com',
        'apartment_name':    raw['apartment_name'],
        'apartment_id':      pd.NA,
        'check_in':          raw['check_in'],
        'check_out':         raw['check_out'],
        'booking_date':      raw['booking_date'],
        'nights':            raw['nights'],
        'adults':            raw['adults'],
        'children':          pd.NA,
        'gross_amount':      raw['gross_amount'],
        'commission_pct':    raw['commission_pct'],
        'commission_amount': raw['commission_amount'],
        'net_amount':        raw['net_amount'],
        'currency':          raw.get('Currency', pd.Series(['EUR']*len(raw))).fillna('EUR'),
        'status':            raw['status_raw'],
        'cancelled':         raw['cancelled'],
        'country':           raw['country'],
        'guest_name':        raw.get('Guest name', pd.Series([np.nan]*len(raw))),
    })

    out = out.drop_duplicates(subset=['reservation_id', 'check_in'])
    print(f"  Statements: {len(out)} filas cargadas, rango {out['check_in'].min().date()} → {out['check_in'].max().date()}")
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# FUENTE 3 — Smoobu (2025–2026, todos los canales)
# ═══════════════════════════════════════════════════════════════════════════════
def load_smoobu() -> pd.DataFrame:
    """Carga el export completo de Smoobu. Aporta apartment_id y canales no-Booking."""
    f = RAW / 'f_reservas_smoobu.csv'
    if not f.exists():
        print("  WARN: f_reservas_smoobu.csv no encontrado")
        return pd.DataFrame()

    raw = pd.read_csv(f, sep=';', decimal=',', encoding='utf-8-sig', on_bad_lines='skip')
    print(f"  Smoobu raw: {len(raw)} filas")

    raw['check_in']     = pd.to_datetime(raw['arrival'], errors='coerce')
    raw['check_out']    = pd.to_datetime(raw['departure'], errors='coerce')
    raw['booking_date'] = pd.to_datetime(raw.get('created_at'), errors='coerce')
    raw['reservation_id'] = pd.to_numeric(raw['reservation_id'], errors='coerce').astype('Int64')
    raw['gross_amount']   = pd.to_numeric(raw['price'], errors='coerce')
    raw['commission_amount'] = pd.to_numeric(raw.get('commission'), errors='coerce')
    raw['commission_pct'] = np.where(
        raw['gross_amount'] > 0,
        (raw['commission_amount'] / raw['gross_amount'] * 100).round(2),
        np.nan
    )
    raw['net_amount'] = raw['gross_amount'] - raw['commission_amount'].fillna(0)
    raw['nights']     = pd.to_numeric(raw.get('noches'), errors='coerce').astype('Int64')
    mask = raw['nights'].isna() | (raw['nights'] == 0)
    raw.loc[mask, 'nights'] = (raw.loc[mask, 'check_out'] - raw.loc[mask, 'check_in']).dt.days

    status_raw = raw.get('status', pd.Series(['']*len(raw))).fillna('').str.upper()
    cancelled_col = raw.get('cancelled', pd.Series([0]*len(raw)))
    cancelled = (cancelled_col == 1) | (cancelled_col == True) | status_raw.isin(['CANCELLED'])

    out = pd.DataFrame({
        'reservation_id':    raw['reservation_id'],
        'source':            'smoobu',
        'channel':           raw.get('channel_name', pd.Series(['Unknown']*len(raw))).fillna('Unknown'),
        'apartment_name':    raw.get('apartment_name', pd.Series([np.nan]*len(raw))),
        'apartment_id':      pd.to_numeric(raw.get('apartment_id'), errors='coerce').astype('Int64'),
        'check_in':          raw['check_in'],
        'check_out':         raw['check_out'],
        'booking_date':      raw['booking_date'],
        'nights':            raw['nights'],
        'adults':            pd.to_numeric(raw.get('adults'), errors='coerce').astype('Int64'),
        'children':          pd.to_numeric(raw.get('children'), errors='coerce').astype('Int64'),
        'gross_amount':      raw['gross_amount'],
        'commission_pct':    raw['commission_pct'],
        'commission_amount': raw['commission_amount'],
        'net_amount':        raw['net_amount'],
        'currency':          raw.get('currency', pd.Series(['EUR']*len(raw))).fillna('EUR'),
        'status':            status_raw,
        'cancelled':         cancelled.astype(bool),
        'country':           raw.get('guest_country', pd.Series([np.nan]*len(raw))),
        'guest_name':        raw.get('guest_name', pd.Series([np.nan]*len(raw))),
    })

    print(f"  Smoobu: {len(out)} filas, rango {out['check_in'].min().date()} → {out['check_in'].max().date()}")
    print(f"  Canales Smoobu: {out['channel'].value_counts().to_dict()}")
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# MERGE Y DEDUP
# ═══════════════════════════════════════════════════════════════════════════════
def merge_and_dedup(xls: pd.DataFrame, stmt: pd.DataFrame, smoobu: pd.DataFrame) -> pd.DataFrame:
    """
    Estrategia de dedup:
    1. Statements enriquece a XLS (mismo reservation_id, Booking.com).
       Se queda la fila de Statements (tiene country + adults + final_amount).
    2. Smoobu 2025+ no solapa con XLS (XLS termina en 2024). Se concatena directamente.
    3. Smoobu Booking.com 2025 sí puede solapar con Statements 2025.
       Se prioriza Smoobu (tiene apartment_id).
    """
    flags_log = []

    # ── Paso 1: enriquecer XLS con country/adults de Statements ──────────────
    stmt_enrich = stmt[['reservation_id', 'country', 'adults', 'nights',
                         'gross_amount', 'commission_pct', 'commission_amount',
                         'net_amount', 'apartment_name']].copy()
    stmt_enrich = stmt_enrich.drop_duplicates('reservation_id')

    xls_enriched = xls.copy()
    xls_enriched = xls_enriched.merge(
        stmt_enrich.rename(columns={
            'country': '_country', 'adults': '_adults', 'nights': '_nights',
            'gross_amount': '_gross', 'commission_pct': '_cpct',
            'commission_amount': '_camt', 'net_amount': '_net',
            'apartment_name': '_apt'
        }),
        on='reservation_id', how='left'
    )
    # Rellenar campos null en XLS con los de Statements
    xls_enriched['country']           = xls_enriched['_country']
    xls_enriched['adults']            = xls_enriched['adults'].combine_first(xls_enriched['_adults'])
    xls_enriched['apartment_name']    = xls_enriched['apartment_name'].combine_first(xls_enriched['_apt'])
    xls_enriched = xls_enriched.drop(columns=[c for c in xls_enriched.columns if c.startswith('_')])

    # IDs que ya están en XLS → los quitamos de Statements para no duplicar
    xls_ids = set(xls_enriched['reservation_id'].dropna())
    stmt_only = stmt[~stmt['reservation_id'].isin(xls_ids)].copy()

    # Anotar duplicados encontrados
    n_xref = stmt['reservation_id'].isin(xls_ids).sum()
    flags_log.append(f"XLS↔Statements solapamiento: {n_xref} reservas comunes (enriquecidas, no duplicadas)")

    # ── Paso 2: Smoobu Booking.com puede solapar con Statements 2025 ─────────
    smoobu_bk = smoobu[smoobu['channel'] == 'Booking.com']
    smoobu_ids = set(smoobu_bk['reservation_id'].dropna())
    stmt_only = stmt_only[~stmt_only['reservation_id'].isin(smoobu_ids)]
    n_smoobu_xref = len(stmt[stmt['reservation_id'].isin(smoobu_ids)])
    flags_log.append(f"Smoobu↔Statements solapamiento: {n_smoobu_xref} reservas (se prioriza Smoobu)")

    # ── Paso 3: concatenar todo ───────────────────────────────────────────────
    df = pd.concat([xls_enriched, stmt_only, smoobu], ignore_index=True)

    # ── Dedup final por reservation_id (prioridad: smoobu > statements > xls) ─
    priority = {'smoobu': 0, 'statements_booking': 1, 'xls_booking': 2}
    df['_prio'] = df['source'].map(priority).fillna(9)
    df = df.sort_values('_prio').drop_duplicates('reservation_id', keep='first')
    df = df.drop(columns=['_prio'])

    print(f"\n  Total tras dedup: {len(df)} reservas únicas")
    return df, flags_log


# ═══════════════════════════════════════════════════════════════════════════════
# ENRIQUECIMIENTO Y FLAGS
# ═══════════════════════════════════════════════════════════════════════════════
def enrich_and_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas derivadas y flags de calidad."""

    # Building
    df['building'] = df['apartment_name'].apply(infer_building)

    # Lead time
    df['lead_time_days'] = (df['check_in'] - df['booking_date']).dt.days
    df.loc[df['lead_time_days'] < 0, 'lead_time_days'] = 0

    # ADR
    df['adr'] = np.where(
        (df['nights'] > 0) & df['gross_amount'].notna(),
        (df['gross_amount'] / df['nights']).round(2),
        np.nan
    )
    df['adr_net'] = np.where(
        (df['nights'] > 0) & df['net_amount'].notna(),
        (df['net_amount'] / df['nights']).round(2),
        np.nan
    )

    # Flags de calidad
    flags = []
    flags.append(np.where(df['apartment_name'].isna(), FLAGS['NO_APARTMENT'], ''))
    flags.append(np.where(df['booking_date'].isna(), FLAGS['NO_BOOKING_DATE'], ''))
    flags.append(np.where((df['nights'] <= 0) | df['nights'].isna(), FLAGS['NEGATIVE_NIGHTS'], ''))
    flags.append(np.where(
        (df['gross_amount'] == 0) & (~df['cancelled']),
        FLAGS['ZERO_PRICE_ACTIVE'], ''
    ))
    flags.append(np.where(df['country'].isna(), FLAGS['NO_COUNTRY'], ''))

    df['data_flags'] = [
        '|'.join(f for f in row_flags if f)
        for row_flags in zip(*flags)
    ]

    # Tipos finales
    df['check_in']  = pd.to_datetime(df['check_in'])
    df['check_out'] = pd.to_datetime(df['check_out'])
    df['booking_date'] = pd.to_datetime(df['booking_date'])
    df['year']  = df['check_in'].dt.year
    df['month'] = df['check_in'].dt.month

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE DE CALIDAD
# ═══════════════════════════════════════════════════════════════════════════════
def generate_quality_report(df: pd.DataFrame, flags_log: list, output_path: Path):
    """Genera 00_data_quality.md con estadísticas de completitud y anomalías."""

    total = len(df)
    active = df[~df['cancelled']]

    lines = [
        "# Reporte de Calidad de Datos — Fase 0",
        f"\n**Fecha de generación:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        f"\n## Resumen General\n",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Total reservas unificadas | {total:,} |",
        f"| Reservas activas (no canceladas) | {len(active):,} |",
        f"| Canceladas | {df['cancelled'].sum():,} ({df['cancelled'].mean()*100:.1f}%) |",
        f"| Rango fechas check-in | {df['check_in'].min().date()} → {df['check_in'].max().date()} |",
        f"| Edificios identificados | {df['building'].nunique()} |",
        f"| Fuentes integradas | XLS Booking, Statements Booking, Smoobu |",
        "",
        "## Registros por Fuente\n",
        "| Fuente | Registros | % del total |",
        "|--------|-----------|-------------|",
    ]
    for src, cnt in df['source'].value_counts().items():
        lines.append(f"| {src} | {cnt:,} | {cnt/total*100:.1f}% |")

    lines += [
        "",
        "## Registros por Canal\n",
        "| Canal | Registros | % del total |",
        "|-------|-----------|-------------|",
    ]
    for ch, cnt in df['channel'].value_counts().items():
        lines.append(f"| {ch} | {cnt:,} | {cnt/total*100:.1f}% |")

    lines += [
        "",
        "## Registros por Edificio\n",
        "| Edificio | Reservas activas | Reservas totales |",
        "|----------|-----------------|-----------------|",
    ]
    for bld in sorted(df['building'].unique()):
        tot = (df['building'] == bld).sum()
        act = ((df['building'] == bld) & ~df['cancelled']).sum()
        lines.append(f"| {bld} | {act:,} | {tot:,} |")

    lines += [
        "",
        "## Completitud por Columna\n",
        "| Columna | % Completo | Nulos |",
        "|---------|-----------|-------|",
    ]
    key_cols = ['reservation_id', 'channel', 'apartment_name', 'building',
                'check_in', 'check_out', 'nights', 'booking_date', 'adults',
                'gross_amount', 'commission_pct', 'net_amount', 'country',
                'lead_time_days', 'adr']
    for col in key_cols:
        if col in df.columns:
            pct = df[col].notna().mean() * 100
            nulls = df[col].isna().sum()
            lines.append(f"| {col} | {pct:.1f}% | {nulls:,} |")

    lines += [
        "",
        "## Flags de Calidad\n",
        "| Flag | Registros afectados |",
        "|------|-------------------|",
    ]
    all_flags_flat = '|'.join(df['data_flags'].fillna(''))
    for flag_key, flag_val in FLAGS.items():
        cnt = all_flags_flat.count(flag_val)
        lines.append(f"| {flag_val} | {cnt:,} |")

    lines += [
        "",
        "## Log de Deduplicación\n",
    ]
    for entry in flags_log:
        lines.append(f"- {entry}")

    lines += [
        "",
        "## Decisiones y Supuestos\n",
        "- **Prioridad de fuentes en dedup:** Smoobu > Statements > XLS",
        "- **Enriquecimiento XLS:** campos `country` y `adults` obtenidos de Statements por `reservation_id`",
        "- **Airbnb histórico:** solo disponible como agregado por apartamento (f_airbnb_earnings.csv). Las reservas individuales Airbnb solo existen desde 2025-01 (vía Smoobu).",
        "- **guest_country:** 0% en todas las fuentes Smoobu. Solo disponible en Booking Statements (2021-2025).",
        "- **Noches negativas/cero:** las reservas CANCELLED con check_in=check_out se marcan con flag `noches_negativas` pero se conservan.",
        "- **Edificio UNKNOWN:** apartamentos cuyo nombre no coincide con el mapa de keywords. Revisar manualmente.",
        "",
        "## Archivos de Salida\n",
        "- `data/processed/reservas_unified.parquet` — dataset unificado",
    ]

    report_text = '\n'.join(lines)
    output_path.write_text(report_text, encoding='utf-8')
    print(f"\n  Reporte guardado en: {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("=" * 60)
    print("FASE 0 — ETL UNIFICACIÓN DE RESERVAS")
    print("=" * 60)

    print("\n[1/4] Cargando XLS Booking (2019-2024)...")
    xls = load_xls_booking()

    print("\n[2/4] Cargando Booking Statements (2021-2025)...")
    stmt = load_booking_statements()

    print("\n[3/4] Cargando Smoobu (2025-2026)...")
    smoobu = load_smoobu()

    print("\n[4/4] Mergeando y deduplicando...")
    df, flags_log = merge_and_dedup(xls, stmt, smoobu)
    df = enrich_and_flag(df)

    # Guardar parquet
    out_file = OUT_DATA / 'reservas_unified.parquet'
    df.to_parquet(out_file, index=False)
    print(f"  Guardado: {out_file}  ({len(df):,} filas, {df.shape[1]} columnas)")

    # Reporte de calidad
    generate_quality_report(df, flags_log, OUT_REPORTS / '00_data_quality.md')

    print("\n" + "=" * 60)
    print("FASE 0 COMPLETADA")
    print(f"  Reservas unificadas: {len(df):,}")
    print(f"  Columnas: {list(df.columns)}")
    print("=" * 60)
