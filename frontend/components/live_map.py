"""Streamlit HTML component — live Leaflet map with WebSocket telemetry."""

import streamlit.components.v1 as components

_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; padding:0; background:#0a0f1e; }}
  #map {{ width:100%; height:{height}px; border-radius:10px; }}
  .drone-label {{
    font: bold 11px 'Sora', sans-serif;
    color: #00e5ff;
    text-shadow: 0 0 4px rgba(0,229,255,.6);
  }}
  #status {{
    position:absolute; bottom:8px; left:8px; z-index:800;
    background:rgba(10,15,30,.85); color:#94a3b8; padding:6px 12px;
    border-radius:6px; font:12px/1.4 monospace; pointer-events:none;
  }}
</style>
</head>
<body>
<div id="map"></div>
<div id="status">connecting&hellip;</div>
<script>
var map = L.map('map', {{ scrollWheelZoom: true }}).setView([13.0, 77.6], 12);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; OSM contributors'
}}).addTo(map);

var markers = {{}};
var statusEl = document.getElementById('status');

function droneIcon(battery) {{
  var hue = battery > 50 ? 140 : (battery > 25 ? 40 : 0);
  return L.divIcon({{
    className: 'drone-label',
    html: '<svg width="28" height="28" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="hsl('+hue+',80%,45%)" opacity="0.85"/><text x="12" y="16" text-anchor="middle" font-size="10" fill="#fff">&#9992;</text></svg>',
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  }});
}}

function connect() {{
  var ws = new WebSocket("{ws_url}");
  ws.onopen = function() {{ statusEl.textContent = 'live'; }};
  ws.onclose = function() {{
    statusEl.textContent = 'reconnecting\u2026';
    setTimeout(connect, 2000);
  }};
  ws.onerror = function() {{ ws.close(); }};
  ws.onmessage = function(e) {{
    var msg = JSON.parse(e.data);
    if (msg.type !== 'telemetry_update') return;
    msg.drones.forEach(function(d) {{
      var id = d.drone_id;
      var ll = [d.latitude, d.longitude];
      if (markers[id]) {{
        markers[id].setLatLng(ll);
        markers[id].setIcon(droneIcon(d.battery_percent));
        markers[id].setPopupContent(
          '<b>'+id+'</b><br>Alt: '+d.altitude_msl.toFixed(1)+'m<br>Speed: '+d.speed_ms.toFixed(1)+' m/s<br>Batt: '+d.battery_percent.toFixed(1)+'%<br>Mode: '+d.mode
        );
      }} else {{
        markers[id] = L.marker(ll, {{ icon: droneIcon(d.battery_percent) }})
          .addTo(map)
          .bindPopup(id);
      }}
    }});
    statusEl.textContent = 'live \u00b7 '+msg.drones.length+' drones \u00b7 '+new Date(msg.timestamp).toLocaleTimeString();
  }};
}}
connect();
</script>
</body>
</html>
"""


def render_live_map(api_url: str, height: int = 500):
    """Embed a live Leaflet map that streams drone positions over WebSocket."""
    ws_url = api_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = ws_url.rstrip("/") + "/api/v1/telemetry/ws"
    html = _TEMPLATE.format(ws_url=ws_url, height=height)
    components.html(html, height=height + 10, scrolling=False)
