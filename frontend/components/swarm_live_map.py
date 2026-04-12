"""
Swarm Live Map component.

Renders a Leaflet map inside a streamlit HTML component that opens a
WebSocket to /api/v1/swarm/obstacles/{session_id}/stream and draws:

  • Drone markers (coloured, moving on real map tiles)
  • Drone trails (last N positions)
  • Sensor rays: ultrasonic (yellow), LiDAR (green), radar circle (blue)
  • Comm links: dashed blue → base station (cellular), solid green → peers (RF D2D)
  • Obstacle circles (red, variable radius, appear/disappear dynamically)
  • Start ▲ and End ✕ markers (static, placed once)
  • Status bar: time, obstacles, arrived drones, avg throughput
"""

from __future__ import annotations
import json
import streamlit.components.v1 as components

_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body  {{ margin:0; padding:0; background:#0b111c; }}
  #map  {{ width:100%; height:{height}px; }}
  #hud  {{
    position:absolute; bottom:8px; left:8px; z-index:900;
    background:rgba(11,17,28,.88); color:#94a3b8;
    padding:6px 12px; border-radius:6px;
    font:11px/1.5 monospace; pointer-events:none;
    border:1px solid #1e2d45;
  }}
</style>
</head>
<body>
<div id="map"></div>
<div id="hud">connecting…</div>
<script>
// ── Constants ─────────────────────────────────────────────────────────────
var WS_URL      = "{ws_url}";
var COLORS      = {colors};
var REF_LAT     = {ref_lat};
var REF_LON     = {ref_lon};
var GEO_MODE    = {geo_mode};   // true → pos_ll available in frames
var TRAIL_LEN   = 40;
var START_PTS   = {start_pts};  // [[lat,lon], ...]
var END_PTS     = {end_pts};
var N_DRONES    = {n_drones};
var COS_REF     = Math.cos(REF_LAT * Math.PI / 180);

function mToLatLon(x, y) {{
  return [REF_LAT + y / 111320, REF_LON + x / (111320 * COS_REF)];
}}
function droneLatLon(d) {{
  if (GEO_MODE && d.pos_ll) return [d.pos_ll[0], d.pos_ll[1]];
  return mToLatLon(d.pos[0], d.pos[1]);
}}
function obsLatLon(o) {{
  if (GEO_MODE && o.pos_ll) return [o.pos_ll[0], o.pos_ll[1]];
  return mToLatLon(o.pos[0], o.pos[1]);
}}
// radius in metres → Leaflet radius (metres, same units as Circle)
function obsRadiusM(o) {{ return o.radius || 15; }}

// ── Map init ──────────────────────────────────────────────────────────────
var initCenter = (START_PTS.length > 0) ? START_PTS[0] : [REF_LAT, REF_LON];
var map = L.map('map', {{scrollWheelZoom:true, zoomControl:true}})
           .setView(initCenter, 14);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{maxZoom:19, attribution:'&copy; OSM contributors'}}).addTo(map);

var hud = document.getElementById('hud');

// ── Static start / end markers ────────────────────────────────────────────
for (var di = 0; di < N_DRONES; di++) {{
  var col = COLORS[di % COLORS.length];
  if (START_PTS[di]) {{
    L.circleMarker(START_PTS[di], {{radius:6, color:col, fillColor:col,
      fillOpacity:0.9, weight:2}})
     .bindTooltip('D'+(di+1)+' Start').addTo(map);
  }}
  if (END_PTS[di]) {{
    L.circleMarker(END_PTS[di], {{radius:6, color:col, fillColor:'transparent',
      fillOpacity:0, weight:2, dashArray:'5'}})
     .bindTooltip('D'+(di+1)+' End').addTo(map);
  }}
}}

// Base-station marker
var bsLL = mToLatLon(500, 500);
L.circleMarker(bsLL, {{radius:8, color:'#ff4444', fillColor:'#ff4444',
  fillOpacity:0.8}}).bindTooltip('gNB').addTo(map);

// ── Per-drone state ───────────────────────────────────────────────────────
var droneMarkers   = [];
var droneLabels    = [];
var droneTrails    = [];
var trailHistory   = [];
var cellLinks      = [];
var usLines        = [];     // ultrasonic
var lidarLines     = [];     // LIDAR per drone: array of N lines
var radarCircles   = [];
var rfLinkLines    = {{}};    // key "i-j"

for (var i = 0; i < N_DRONES; i++) {{
  var c = COLORS[i % COLORS.length];
  droneMarkers.push(
    L.circleMarker([0,0], {{radius:7, color:c, fillColor:c,
      fillOpacity:0.95, weight:2}}).addTo(map)
  );
  droneLabels.push(
    L.marker([0,0], {{icon: L.divIcon({{
      className:'', html:'<span style="color:'+c+';font:bold 10px monospace;'
        +'text-shadow:0 0 3px #000">D'+(i+1)+'</span>',
      iconSize:[20,12], iconAnchor:[-4,6]
    }})}}).addTo(map)
  );
  droneTrails.push(L.polyline([], {{color:c, weight:1.5, opacity:0.45}}).addTo(map));
  trailHistory.push([]);
  cellLinks.push(L.polyline([], {{color:'#4488ff', weight:1.2,
    dashArray:'6', opacity:0.7}}).addTo(map));
  usLines.push(L.polyline([], {{color:'#ffdd00', weight:2.2, opacity:0.9}}).addTo(map));
  radarCircles.push(L.circle([0,0], {{radius:1, color:'#4488ff', weight:1,
    fillOpacity:0, opacity:0.22}}).addTo(map));
  var rays = [];
  for (var r = 0; r < 24; r++) {{
    rays.push(L.polyline([], {{color:'#33ff77', weight:0.7, opacity:0.5}}).addTo(map));
  }}
  lidarLines.push(rays);
}}

// ── Obstacle circles ──────────────────────────────────────────────────────
var obstacleCircles = {{}};   // key = obs index in current frame

function updateObstacles(obsArr) {{
  // Remove old circles not in current frame
  var newKeys = {{}};
  for (var k = 0; k < obsArr.length; k++) newKeys[k] = true;
  for (var ek in obstacleCircles) {{
    if (!(ek in newKeys)) {{
      map.removeLayer(obstacleCircles[ek]);
      delete obstacleCircles[ek];
    }}
  }}
  // Add / update
  for (var oi = 0; oi < obsArr.length; oi++) {{
    var o   = obsArr[oi];
    var ll  = obsLatLon(o);
    var rad = obsRadiusM(o);
    if (!obstacleCircles[oi]) {{
      obstacleCircles[oi] = L.circle(ll, {{radius:rad, color:'#ff4444',
        fillColor:'#ff4444', fillOpacity:0.30, weight:1.5}}).addTo(map);
    }} else {{
      obstacleCircles[oi].setLatLng(ll).setRadius(rad);
    }}
  }}
}}

// ── Bearing helper (degrees from north) ──────────────────────────────────
function bearingLatLon(fromLL, toLL) {{
  var dLon = (toLL[1] - fromLL[1]) * Math.PI / 180;
  var lat1 = fromLL[0] * Math.PI / 180;
  var lat2 = toLL[0] * Math.PI / 180;
  var y = Math.sin(dLon) * Math.cos(lat2);
  var x = Math.cos(lat1)*Math.sin(lat2) - Math.sin(lat1)*Math.cos(lat2)*Math.cos(dLon);
  return Math.atan2(y, x);   // radians, clockwise from north
}}

function offsetLatLon(ll, distM, bearingRad) {{
  var R = 6371000;
  var lat1 = ll[0] * Math.PI / 180;
  var lon1 = ll[1] * Math.PI / 180;
  var lat2 = Math.asin(Math.sin(lat1)*Math.cos(distM/R)
              + Math.cos(lat1)*Math.sin(distM/R)*Math.cos(bearingRad));
  var lon2 = lon1 + Math.atan2(
    Math.sin(bearingRad)*Math.sin(distM/R)*Math.cos(lat1),
    Math.cos(distM/R) - Math.sin(lat1)*Math.sin(lat2));
  return [lat2*180/Math.PI, lon2*180/Math.PI];
}}

// ── WebSocket ─────────────────────────────────────────────────────────────
function connect() {{
  var ws = new WebSocket(WS_URL);
  hud.textContent = 'connecting…';

  ws.onopen = function() {{ hud.textContent = '● live'; }};
  ws.onclose = function() {{
    hud.textContent = '○ reconnecting…';
    setTimeout(connect, 2500);
  }};
  ws.onerror = function() {{ ws.close(); }};

  ws.onmessage = function(evt) {{
    var msg = JSON.parse(evt.data);
    if (msg.type === 'done') {{
      hud.textContent = '✓ simulation complete — ' + msg.total_frames + ' frames';
      return;
    }}

    var drones = msg.drones || [];
    var obs    = msg.obstacles || [];
    var summ   = msg.summary   || {{}};

    drones.forEach(function(d, i) {{
      if (i >= N_DRONES) return;
      var ll = droneLatLon(d);

      // Trail
      trailHistory[i].push(ll);
      if (trailHistory[i].length > TRAIL_LEN)
        trailHistory[i] = trailHistory[i].slice(-TRAIL_LEN);
      droneTrails[i].setLatLngs(trailHistory[i]);

      // Marker + label
      droneMarkers[i].setLatLng(ll);
      droneLabels[i].setLatLng(ll);

      // Cellular link
      cellLinks[i].setLatLngs([ll, bsLL]);
      cellLinks[i].setStyle({{
        color: d.cellular_ok ? '#4488ff' : '#ff4444',
        dashArray: d.cellular_ok ? '6' : '3'
      }});

      // Ultrasonic — forward beam (towards goal or drift angle)
      if (d.sensors && d.sensors.ultrasonic_m != null) {{
        // Estimate forward bearing from velocity (use pos vs end in metres)
        var angle = 0;  // fallback north; JS doesn't know heading directly
        // Use a simple heuristic: angle from current to previous trail point
        if (trailHistory[i].length >= 2) {{
          var prev = trailHistory[i][trailHistory[i].length - 2];
          angle = bearingLatLon(prev, ll);
        }}
        var tip = offsetLatLon(ll, d.sensors.ultrasonic_m, angle);
        usLines[i].setLatLngs([ll, tip]);
      }} else {{
        usLines[i].setLatLngs([]);
      }}

      // LiDAR rays
      if (d.sensors && d.sensors.lidar_rays_m) {{
        d.sensors.lidar_rays_m.forEach(function(dist, ri) {{
          var ang = (2 * Math.PI / 24) * ri;
          var tip = offsetLatLon(ll, dist, ang);
          lidarLines[i][ri].setLatLngs([ll, tip]);
        }});
      }}

      // Radar circle
      if (d.sensors && d.sensors.radar_range_m) {{
        radarCircles[i].setLatLng(ll).setRadius(d.sensors.radar_range_m);
      }}
    }});

    // RF D2D links
    var pairs = (summ.rf_pairs || []);
    // Clear old RF links
    for (var k in rfLinkLines) {{ map.removeLayer(rfLinkLines[k]); }}
    rfLinkLines = {{}};
    pairs.forEach(function(p) {{
      var a = p[0], b = p[1];
      if (a >= drones.length || b >= drones.length) return;
      var key = a + '-' + b;
      rfLinkLines[key] = L.polyline([droneLatLon(drones[a]), droneLatLon(drones[b])],
        {{color:'#33ff77', weight:1.8, opacity:0.75}}).addTo(map);
    }});

    // Obstacles
    updateObstacles(obs);

    // HUD
    hud.innerHTML =
      't = ' + (msg.time_s || 0).toFixed(1) + ' s' +
      ' &nbsp;|&nbsp; Obstacles: ' + (summ.total_obstacles || 0) +
      ' &nbsp;|&nbsp; Arrived: ' + (summ.arrived || 0) + '/' + N_DRONES +
      ' &nbsp;|&nbsp; Cell OK: ' + (summ.active_cellular || 0) + '/' + N_DRONES +
      ' &nbsp;|&nbsp; RF: ' + (summ.active_rf_links || 0) +
      ' &nbsp;|&nbsp; Thr: ' + (summ.avg_throughput_mbps || 0).toFixed(2) + ' Mbps';
  }};
}}

connect();
</script>
</body>
</html>"""


def render_swarm_live_map(
    ws_url:       str,
    drone_colors: list[str],
    ref_lat:      float,
    ref_lon:      float,
    n_drones:     int,
    start_pts:    list[list[float]],   # [[lat, lon], ...]
    end_pts:      list[list[float]],
    geo_mode:     bool = True,
    height:       int  = 500,
) -> None:
    """Embed the Leaflet live-map WebSocket component."""
    html = _TEMPLATE.format(
        ws_url=ws_url,
        colors=json.dumps(drone_colors),
        ref_lat=ref_lat,
        ref_lon=ref_lon,
        geo_mode=str(geo_mode).lower(),
        n_drones=n_drones,
        start_pts=json.dumps(start_pts),
        end_pts=json.dumps(end_pts),
        height=height,
    )
    components.html(html, height=height + 20)
