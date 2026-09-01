"""
Build interactive Leaflet.js market map HTML for Bilbao STR analytics.
Embeds GeoJSON choropleth + listing scatter + portfolio building markers.
Output: outputs/BilbaoMarketMap.html
"""
import json
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA = BASE / "data" / "public"
OUT  = BASE / "outputs"

# Load pre-processed JSON files
with open(DATA / "map_geojson.json", "r", encoding="utf-8") as f:
    gj_content = f.read()
with open(DATA / "map_listings.json", "r") as f:
    listings_content = f.read()
with open(DATA / "map_buildings.json", "r") as f:
    buildings_content = f.read()

# ----- HTML TEMPLATE -----
HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RevenuePilot — Mapa de Mercado Bilbao | STR Analytics</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',system-ui,sans-serif; background:#0f172a; color:#e2e8f0; }

.header {
  position:fixed; top:0; left:0; right:0; z-index:2000;
  background:rgba(15,23,42,0.97); backdrop-filter:blur(12px);
  border-bottom:1px solid #1e3a5f;
  display:flex; align-items:center; gap:16px;
  padding:10px 20px; height:58px;
}
.logo { font-size:1.25rem; font-weight:800; color:#38bdf8; letter-spacing:-0.5px; }
.logo span { color:#818cf8; }
.header-sub { font-size:0.72rem; color:#64748b; margin-top:2px; }
.header-stats { margin-left:auto; display:flex; gap:18px; }
.hstat { text-align:center; }
.hstat-val { font-size:0.95rem; font-weight:700; color:#38bdf8; }
.hstat-lbl { font-size:0.6rem; color:#64748b; text-transform:uppercase; }

#map { position:fixed; top:58px; left:0; right:340px; bottom:0; z-index:1; }

.sidebar {
  position:fixed; top:58px; right:0; width:340px; bottom:0;
  background:#0f172a; border-left:1px solid #1e3a5f;
  overflow-y:auto; z-index:1500; display:flex; flex-direction:column;
}
.sidebar-section { padding:14px 16px; border-bottom:1px solid #1e293b; }
.sidebar-title {
  font-size:0.65rem; font-weight:700; color:#64748b;
  text-transform:uppercase; letter-spacing:1.2px; margin-bottom:10px;
}

.layer-btn {
  display:flex; align-items:center; gap:10px;
  padding:7px 10px; border-radius:8px; cursor:pointer;
  margin-bottom:5px; transition:background 0.2s;
  border:1px solid transparent;
}
.layer-btn:hover { background:#1e293b; }
.layer-btn.active { background:#1e3a5f; border-color:#38bdf8; }
.layer-dot { width:14px; height:14px; border-radius:50%; flex-shrink:0; border:2px solid rgba(255,255,255,0.25); }
.layer-label { font-size:0.8rem; color:#cbd5e1; flex:1; }
.layer-count { font-size:0.68rem; color:#64748b; background:#1e293b; padding:1px 6px; border-radius:10px; }

.building-card {
  padding:10px 12px; border-radius:10px;
  background:#1e293b; margin-bottom:7px;
  border:1px solid #334155; cursor:pointer; transition:all 0.2s;
}
.building-card:hover { border-color:#38bdf8; background:#1e3a5f; transform:translateX(2px); }
.building-name { font-size:0.8rem; font-weight:600; color:#e2e8f0; margin-bottom:6px; }
.building-metrics { display:flex; gap:8px; }
.bm { text-align:center; flex:1; }
.bm-val { font-size:0.88rem; font-weight:700; }
.bm-lbl { font-size:0.58rem; color:#64748b; text-transform:uppercase; }
.pct-bar { height:3px; background:#334155; border-radius:2px; margin-top:7px; }
.pct-fill { height:100%; border-radius:2px; transition:width 0.4s; }

#info-panel {
  background:#1e293b; border-radius:10px; padding:12px;
  border:1px solid #334155;
}
#info-panel h4 { font-size:0.83rem; color:#38bdf8; margin-bottom:8px; }
#info-panel p { font-size:0.76rem; color:#94a3b8; line-height:1.5; }
.info-grid { display:grid; grid-template-columns:1fr 1fr; gap:7px; margin-top:8px; }
.ig { background:#0f172a; padding:8px; border-radius:7px; text-align:center; }
.ig-val { font-size:0.88rem; font-weight:700; color:#e2e8f0; }
.ig-lbl { font-size:0.58rem; color:#64748b; text-transform:uppercase; }

.market-kpi { display:grid; grid-template-columns:1fr 1fr; gap:7px; }
.mkpi { background:#1e293b; border-radius:8px; padding:9px; text-align:center; border:1px solid #334155; }
.mkpi-val { font-size:0.95rem; font-weight:700; color:#38bdf8; }
.mkpi-lbl { font-size:0.6rem; color:#64748b; text-transform:uppercase; margin-top:2px; }

.legend-row { display:flex; align-items:center; gap:8px; margin-bottom:5px; }
.legend-box { width:16px; height:12px; border-radius:3px; flex-shrink:0; border:1px solid rgba(255,255,255,0.12); }
.legend-label { font-size:0.73rem; color:#94a3b8; }

::-webkit-scrollbar { width:5px; }
::-webkit-scrollbar-track { background:#0f172a; }
::-webkit-scrollbar-thumb { background:#334155; border-radius:3px; }

.leaflet-tooltip {
  background:rgba(15,23,42,0.96) !important; border:1px solid #334155 !important;
  color:#e2e8f0 !important; font-size:0.73rem; border-radius:8px !important;
  padding:7px 11px !important; box-shadow:0 4px 20px rgba(0,0,0,0.6) !important;
}
.leaflet-popup-content-wrapper {
  background:#1e293b !important; border:1px solid #334155 !important;
  border-radius:12px !important; color:#e2e8f0 !important;
  box-shadow:0 8px 32px rgba(0,0,0,0.7) !important;
}
.leaflet-popup-tip { background:#1e293b !important; }
.leaflet-popup-content { margin:14px 18px !important; min-width:210px; }
.popup-title { font-size:0.9rem; font-weight:700; color:#38bdf8; margin-bottom:8px; }
.popup-row { display:flex; justify-content:space-between; padding:4px 0; font-size:0.77rem; border-bottom:1px solid #334155; }
.popup-row:last-child { border-bottom:none; }
.popup-key { color:#94a3b8; }
.popup-val { color:#e2e8f0; font-weight:600; }

.leaflet-control-zoom a { background:#1e293b !important; color:#e2e8f0 !important; border-color:#334155 !important; }
.leaflet-control-zoom a:hover { background:#1e3a5f !important; }
.leaflet-control-attribution { background:rgba(15,23,42,0.8) !important; color:#475569 !important; font-size:0.6rem !important; }
.leaflet-control-attribution a { color:#64748b !important; }
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="logo">Revenue<span>Pilot</span></div>
    <div class="header-sub">Inteligencia de Mercado STR — País Vasco 2025</div>
  </div>
  <div class="header-stats">
    <div class="hstat"><div class="hstat-val">1.561</div><div class="hstat-lbl">Listings Bilbao</div></div>
    <div class="hstat"><div class="hstat-val">€136</div><div class="hstat-lbl">Mediana ADR</div></div>
    <div class="hstat"><div class="hstat-val">47.6%</div><div class="hstat-lbl">Ocupación impl.</div></div>
    <div class="hstat"><div class="hstat-val">33.8%</div><div class="hstat-lbl">Hosts pro</div></div>
    <div class="hstat"><div class="hstat-val">5 edif.</div><div class="hstat-lbl">Portfolio</div></div>
  </div>
</div>

<div id="map"></div>

<div class="sidebar">

  <div class="sidebar-section">
    <div class="sidebar-title">Mercado Bilbao — Inside Airbnb 2025</div>
    <div class="market-kpi">
      <div class="mkpi"><div class="mkpi-val">1.561</div><div class="mkpi-lbl">Listings activos</div></div>
      <div class="mkpi"><div class="mkpi-val">€136</div><div class="mkpi-lbl">Mediana €/noche</div></div>
      <div class="mkpi"><div class="mkpi-val">47.6%</div><div class="mkpi-lbl">Ocup. implícita</div></div>
      <div class="mkpi"><div class="mkpi-val">65.3%</div><div class="mkpi-lbl">Apts enteros</div></div>
      <div class="mkpi"><div class="mkpi-val">63.1%</div><div class="mkpi-lbl">Hosts multi-prop</div></div>
      <div class="mkpi"><div class="mkpi-val">+135%</div><div class="mkpi-lbl">Reviews 2019→2024</div></div>
    </div>
  </div>

  <div class="sidebar-section">
    <div class="sidebar-title">Capas del mapa</div>
    <div class="layer-btn active" id="btn-choropleth" onclick="toggleLayer('choropleth')">
      <div class="layer-dot" style="background:linear-gradient(135deg,#0ea5e9,#7c3aed);border-radius:2px;"></div>
      <div class="layer-label">Coropleta precio por municipio</div>
      <div class="layer-count">207</div>
    </div>
    <div class="layer-btn active" id="btn-listings" onclick="toggleLayer('listings')">
      <div class="layer-dot" style="background:#f59e0b;"></div>
      <div class="layer-label">Listings Airbnb (muestra 700)</div>
      <div class="layer-count">700</div>
    </div>
    <div class="layer-btn active" id="btn-portfolio" onclick="toggleLayer('portfolio')">
      <div class="layer-dot" style="background:#10b981;border-radius:2px;"></div>
      <div class="layer-label">Portfolio — 5 edificios</div>
      <div class="layer-count">5</div>
    </div>
  </div>

  <div class="sidebar-section">
    <div class="sidebar-title">Portfolio vs. Mercado — Click para centrar</div>
    <div id="building-cards"></div>
  </div>

  <div class="sidebar-section" style="flex:1;">
    <div class="sidebar-title">Detalle — Click en el mapa</div>
    <div id="info-panel">
      <p style="color:#475569;font-style:italic;font-size:0.78rem;">Haz click en cualquier municipio, listing o edificio del portfolio para ver sus métricas.</p>
    </div>
  </div>

  <div class="sidebar-section">
    <div class="sidebar-title">Leyenda — Precio mediana (aptos enteros)</div>
    <div class="legend-row"><div class="legend-box" style="background:#0ea5e9;"></div><div class="legend-label">Menos de €75 (Budget)</div></div>
    <div class="legend-row"><div class="legend-box" style="background:#38bdf8;"></div><div class="legend-label">€75–€120 (Economy)</div></div>
    <div class="legend-row"><div class="legend-box" style="background:#818cf8;"></div><div class="legend-label">€120–€180 (Mid-scale)</div></div>
    <div class="legend-row"><div class="legend-box" style="background:#a78bfa;"></div><div class="legend-label">€180–€300 (Upscale)</div></div>
    <div class="legend-row"><div class="legend-box" style="background:#7c3aed;"></div><div class="legend-label">Más de €300 (Luxury)</div></div>
    <div style="margin-top:10px;border-top:1px solid #334155;padding-top:10px;">
      <div class="legend-row">
        <div style="width:16px;height:16px;background:#10b981;border-radius:3px;border:2px solid white;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:900;color:white;flex-shrink:0;">A</div>
        <div class="legend-label">Edificio del portfolio</div>
      </div>
      <div class="legend-row">
        <div style="width:10px;height:10px;background:#f59e0b;border-radius:50%;flex-shrink:0;margin-left:3px;"></div>
        <div class="legend-label" style="margin-left:5px;">Listing Airbnb (muestra)</div>
      </div>
    </div>
    <div style="margin-top:10px;padding:8px;background:#1e293b;border-radius:8px;font-size:0.68rem;color:#64748b;line-height:1.5;">
      Fuente: Inside Airbnb 2025 (datos públicos). Muestra estratificada de 700 listings.<br>
      Portfolio: datos propios anonimizados. Percentil = posición en mercado Bilbao.
    </div>
  </div>

</div>

<script>
// =================== DATA ===================
const GEOJSON_DATA = GJ_PLACEHOLDER;
const LISTINGS_DATA = LISTINGS_PLACEHOLDER;
const BUILDINGS_DATA = BUILDINGS_PLACEHOLDER;

// =================== CONFIG ===================
const TIER_COLORS = {
  'Budget (<€75)': '#0ea5e9',
  'Economy (€75-120)': '#38bdf8',
  'Mid-scale (€120-180)': '#818cf8',
  'Upscale (€180-300)': '#a78bfa',
  'Luxury (>€300)': '#7c3aed'
};
const BUILDING_COLORS = ['#10b981','#f59e0b','#ec4899','#8b5cf6','#ef4444'];
const BUILDING_LETTERS = ['A','B','C','D','E'];

function priceColor(price) {
  if (!price || price < 75) return '#0ea5e9';
  if (price < 120) return '#38bdf8';
  if (price < 180) return '#818cf8';
  if (price < 300) return '#a78bfa';
  return '#7c3aed';
}

// =================== MAP ===================
const map = L.map('map', { center: [43.263, -2.935], zoom: 13 });
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
  subdomains: 'abcd', maxZoom: 19
}).addTo(map);

const choroplethLayer = L.layerGroup().addTo(map);
const listingsLayer   = L.layerGroup().addTo(map);
const portfolioLayer  = L.layerGroup().addTo(map);
const layerMap = {
  choropleth: { group: choroplethLayer, active: true },
  listings:   { group: listingsLayer,   active: true },
  portfolio:  { group: portfolioLayer,  active: true }
};

function toggleLayer(name) {
  const l = layerMap[name];
  const btn = document.getElementById('btn-' + name);
  if (l.active) { map.removeLayer(l.group); btn.classList.remove('active'); }
  else          { map.addLayer(l.group);    btn.classList.add('active'); }
  l.active = !l.active;
}

// =================== CHOROPLETH ===================
function choroplethStyle(feature) {
  const p = feature.properties;
  return {
    fillColor: priceColor(p.median_price || 0),
    fillOpacity: (p.listing_count || 0) > 0 ? 0.3 : 0.04,
    color: '#334155',
    weight: 0.7,
    opacity: 0.6
  };
}
function choroplethHover(feature) {
  return { fillOpacity: 0.65, color: '#64748b', weight: 1.5 };
}

const choroLayer = L.geoJSON(GEOJSON_DATA, {
  style: choroplethStyle,
  onEachFeature: function(feature, layer) {
    const p = feature.properties;
    if (!p.listing_count) return;
    const occ = p.implied_occupancy != null ? p.implied_occupancy.toFixed(1) + '%' : 'N/A';
    const pro = p.pro_host_pct != null ? p.pro_host_pct.toFixed(0) + '%' : '—';
    const rev = (p.total_reviews_ltm || 0).toLocaleString('es-ES');

    layer.bindTooltip(
      '<b>' + p.neighbourhood + '</b><br>' +
      p.listing_count + ' listings &middot; &euro;' + (p.median_price || 0) + ' mediana',
      { sticky: true }
    );

    layer.on('click', function() {
      document.getElementById('info-panel').innerHTML =
        '<h4>&#128205; ' + p.neighbourhood + ' (' + (p.neighbourhood_group || '') + ')</h4>' +
        '<div class="info-grid">' +
        '<div class="ig"><div class="ig-val">' + p.listing_count + '</div><div class="ig-lbl">Listings</div></div>' +
        '<div class="ig"><div class="ig-val">&euro;' + (p.median_price || '—') + '</div><div class="ig-lbl">Mediana/noche</div></div>' +
        '<div class="ig"><div class="ig-val">' + occ + '</div><div class="ig-lbl">Ocup. impl.</div></div>' +
        '<div class="ig"><div class="ig-val">' + pro + '</div><div class="ig-lbl">Hosts pro</div></div>' +
        '</div>' +
        '<p style="margin-top:8px;font-size:0.72rem;">' + rev + ' reviews últ. 12m</p>';
    });
    layer.on('mouseover', function() { layer.setStyle(choroplethHover(feature)); });
    layer.on('mouseout',  function() { layer.setStyle(choroplethStyle(feature)); });
  }
}).addTo(choroplethLayer);

// =================== LISTINGS SCATTER ===================
LISTINGS_DATA.forEach(function(d) {
  if (!d.latitude || !d.longitude) return;
  const color = TIER_COLORS[d.price_tier] || '#64748b';
  const r = d.room_type === 'Entire home/apt' ? 5 : 3.5;
  const circle = L.circleMarker([d.latitude, d.longitude], {
    radius: r, fillColor: color, color: 'rgba(0,0,0,0.3)',
    weight: 0.5, fillOpacity: 0.72
  });
  circle.bindTooltip(
    '&euro;' + Math.round(d.price_clean || 0) + '/noche &middot; ' + (d.price_tier || '') + '<br>' +
    (d.room_type || '') + ' &middot; ' + (d.host_type || '') + '<br>' +
    (d.number_of_reviews_ltm || 0) + ' reviews &uacute;lt. 12m',
    { sticky: true }
  );
  circle.on('click', function() {
    document.getElementById('info-panel').innerHTML =
      '<h4>&#127968; Listing Airbnb</h4>' +
      '<div class="info-grid">' +
      '<div class="ig"><div class="ig-val">&euro;' + Math.round(d.price_clean || 0) + '</div><div class="ig-lbl">Precio/noche</div></div>' +
      '<div class="ig"><div class="ig-val">' + (d.number_of_reviews_ltm || 0) + '</div><div class="ig-lbl">Reviews LTM</div></div>' +
      '</div>' +
      '<p style="margin-top:8px;">' + (d.price_tier || '') + '<br>' +
      (d.room_type || '') + '<br>Host: ' + (d.host_type || '') + '</p>';
  });
  circle.addTo(listingsLayer);
});

// =================== PORTFOLIO BUILDINGS ===================
BUILDINGS_DATA.forEach(function(b, i) {
  const isAbove  = b.vs_market > 0;
  const color    = BUILDING_COLORS[i];
  const letter   = BUILDING_LETTERS[i];
  const pctColor = b.percentile_est >= 50 ? '#34d399' : (b.percentile_est >= 40 ? '#fbbf24' : '#f87171');
  const gapColor = isAbove ? '#34d399' : (b.vs_market > -20 ? '#fbbf24' : '#f87171');

  const icon = L.divIcon({
    html: '<div style="width:36px;height:36px;background:' + color + ';' +
      'border:3px solid white;border-radius:5px;' +
      'display:flex;align-items:center;justify-content:center;' +
      'font-size:15px;font-weight:900;color:white;' +
      'box-shadow:0 4px 15px rgba(0,0,0,0.7);cursor:pointer;">' + letter + '</div>',
    iconSize: [36, 36], iconAnchor: [18, 18], className: ''
  });

  const upside = b.revenue_upside_annual > 0
    ? '&euro;' + Math.round(b.revenue_upside_annual / 1000) + 'K upside/a&ntilde;o'
    : 'En precio de mercado';

  const marker = L.marker([b.latitude, b.longitude], { icon });
  marker.bindPopup(
    '<div class="popup-title">&#127970; ' + b.building + '</div>' +
    '<div class="popup-row"><span class="popup-key">Nuestro ADR</span><span class="popup-val">&euro;' + b.our_adr + '/noche</span></div>' +
    '<div class="popup-row"><span class="popup-key">Mediana mercado</span><span class="popup-val">&euro;' + b.market_median_adr + '/noche</span></div>' +
    '<div class="popup-row"><span class="popup-key">vs. Mercado</span><span class="popup-val" style="color:' + gapColor + '">' + (isAbove ? '+' : '') + b.vs_market + '&euro;</span></div>' +
    '<div class="popup-row"><span class="popup-key">Percentil mercado</span><span class="popup-val" style="color:' + pctColor + '">P' + b.percentile_est + '</span></div>' +
    '<div class="popup-row"><span class="popup-key">Ocupaci&oacute;n</span><span class="popup-val">' + b.our_occupancy + '%</span></div>' +
    '<div class="popup-row"><span class="popup-key">Score Booking</span><span class="popup-val">' + b.our_score + '/10</span></div>' +
    '<div class="popup-row"><span class="popup-key">Oportunidad precio</span><span class="popup-val" style="color:#fbbf24;">' + upside + '</span></div>'
  );
  marker.on('click', function() {
    document.getElementById('info-panel').innerHTML =
      '<h4>&#127970; Edificio ' + letter + ' &mdash; ' + b.building + '</h4>' +
      '<div class="info-grid">' +
      '<div class="ig"><div class="ig-val" style="color:' + pctColor + '">P' + b.percentile_est + '</div><div class="ig-lbl">Percentil</div></div>' +
      '<div class="ig"><div class="ig-val">&euro;' + b.our_adr + '</div><div class="ig-lbl">Nuestro ADR</div></div>' +
      '<div class="ig"><div class="ig-val" style="color:' + gapColor + '">' + (isAbove ? '+' : '') + b.vs_market + '&euro;</div><div class="ig-lbl">vs Mercado</div></div>' +
      '<div class="ig"><div class="ig-val">' + b.our_occupancy + '%</div><div class="ig-lbl">Ocupaci&oacute;n</div></div>' +
      '</div>' +
      (b.revenue_upside_annual > 0
        ? '<p style="margin-top:8px;color:#fbbf24;font-size:0.77rem;">&#128176; Upside de pricing: &euro;' + Math.round(b.revenue_upside_annual / 1000) + 'K/a&ntilde;o disponibles sin a&ntilde;adir unidades.</p>'
        : '<p style="margin-top:8px;color:#34d399;font-size:0.77rem;">&#10003; Precio competitivo vs. mercado.</p>');
  });
  marker.addTo(portfolioLayer);
});

// =================== SIDEBAR BUILDING CARDS ===================
const cardsEl = document.getElementById('building-cards');
BUILDINGS_DATA.forEach(function(b, i) {
  const isAbove  = b.vs_market > 0;
  const color    = BUILDING_COLORS[i];
  const letter   = BUILDING_LETTERS[i];
  const pctColor = b.percentile_est >= 50 ? '#34d399' : (b.percentile_est >= 40 ? '#fbbf24' : '#f87171');
  const gapColor = isAbove ? '#34d399' : (b.vs_market > -20 ? '#fbbf24' : '#f87171');
  const gapStr   = (isAbove ? '+' : '') + b.vs_market + '€';

  const card = document.createElement('div');
  card.className = 'building-card';
  card.innerHTML =
    '<div class="building-name">' +
    '<span style="background:' + color + ';color:white;padding:1px 7px;border-radius:4px;font-size:0.68rem;font-weight:800;margin-right:6px;">' + letter + '</span>' +
    b.building + '</div>' +
    '<div class="building-metrics">' +
    '<div class="bm"><div class="bm-val">€' + b.our_adr + '</div><div class="bm-lbl">ADR</div></div>' +
    '<div class="bm"><div class="bm-val" style="color:' + gapColor + '">' + gapStr + '</div><div class="bm-lbl">vs Mdo.</div></div>' +
    '<div class="bm"><div class="bm-val" style="color:' + pctColor + '">P' + b.percentile_est + '</div><div class="bm-lbl">Percentil</div></div>' +
    '<div class="bm"><div class="bm-val">' + b.our_occupancy + '%</div><div class="bm-lbl">Ocup.</div></div>' +
    '</div>' +
    '<div class="pct-bar"><div class="pct-fill" style="width:' + b.percentile_est + '%;background:' + pctColor + ';"></div></div>';

  card.onclick = function() {
    map.setView([b.latitude, b.longitude], 16);
  };
  cardsEl.appendChild(card);
});

// Fit map to Bilbao on load
map.fitBounds([[43.24, -2.97], [43.29, -2.90]]);
</script>
</body>
</html>
"""

# Replace placeholders with actual data
HTML = HTML.replace('GJ_PLACEHOLDER', gj_content)
HTML = HTML.replace('LISTINGS_PLACEHOLDER', listings_content)
HTML = HTML.replace('BUILDINGS_PLACEHOLDER', buildings_content)

out_path = OUT / "BilbaoMarketMap.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(HTML)

size_kb = len(HTML) // 1024
print(f"Map saved: {out_path}")
print(f"Total size: {size_kb} KB")
