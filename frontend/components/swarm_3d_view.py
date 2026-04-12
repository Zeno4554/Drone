"""
Swarm 3D View component.

Renders a Three.js WebGL scene inside a Streamlit HTML component that opens
a WebSocket to /api/v1/swarm/obstacles/{session_id}/stream and draws at ~60 fps:

  • Drone spheres (colour-coded, lerp-interpolated for smooth motion)
  • Drone trails (last N positions as a 3D polyline)
  • Obstacle spheres (true 3D, radius-accurate, dynamic spawn/despawn)
  • RF D2D comm links (green lines between active pairs)
  • Cellular links (blue/red lines to base station)
  • Base station (red octahedron)
  • Ground grid
  • Orbital camera (mouse drag = rotate, scroll = zoom, right-drag = pan)
  • HUD status bar
"""

from __future__ import annotations
import json
import streamlit.components.v1 as components

_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body  {{ background:#0b111c; overflow:hidden; }}
  #c    {{ width:100%; height:{height}px; display:block; }}
  #hud3 {{
    position:absolute; bottom:8px; left:8px; z-index:10;
    background:rgba(11,17,28,.88); color:#94a3b8;
    padding:6px 12px; border-radius:6px;
    font:11px/1.5 monospace; pointer-events:none;
    border:1px solid #1e2d45;
  }}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="hud3">connecting…</div>

<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js"></script>

<script>
// ── Injected from Python ──────────────────────────────────────────────────────
var WS_URL   = "{ws_url}";
var N_DRONES = {n_drones};
var COLORS   = {colors};      // array of 0xRRGGBB integers
var AREA     = {area};        // sim XY extent (metres)
var BS_POS   = {bs_pos};      // [x, y, z]
var TRAIL_LEN = 60;

// ── Renderer ──────────────────────────────────────────────────────────────────
var canvas   = document.getElementById('c');
var renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true }});
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(canvas.clientWidth, {height});
renderer.setClearColor(0x0b111c);

// ── Scene + Camera ────────────────────────────────────────────────────────────
var scene  = new THREE.Scene();
var aspect = canvas.clientWidth / {height};
var camera = new THREE.PerspectiveCamera(50, aspect, 1, 8000);
camera.position.set(AREA * 1.4, -AREA * 0.5, AREA * 0.7);
camera.up.set(0, 0, 1);   // Z-up

// ── Orbital controls ──────────────────────────────────────────────────────────
var controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.set(AREA / 2, AREA / 2, 80);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance   = 50;
controls.maxDistance   = 4000;
controls.update();

// ── Lighting ──────────────────────────────────────────────────────────────────
scene.add(new THREE.AmbientLight(0x334466, 3));
var dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight.position.set(AREA, AREA, 800);
scene.add(dirLight);

// ── Ground grid ───────────────────────────────────────────────────────────────
var grid = new THREE.GridHelper(AREA, 20, 0x1e3050, 0x1e3050);
grid.rotation.x = Math.PI / 2;   // XZ → XY plane
grid.position.set(AREA / 2, AREA / 2, 0);
scene.add(grid);

// ── Base station ──────────────────────────────────────────────────────────────
var bsMesh = new THREE.Mesh(
  new THREE.OctahedronGeometry(16, 0),
  new THREE.MeshPhongMaterial({{ color: 0xff4444, emissive: 0xff2222,
                                  emissiveIntensity: 0.6 }})
);
bsMesh.position.set(BS_POS[0], BS_POS[1], BS_POS[2]);
scene.add(bsMesh);

// ── Drone meshes + trails ─────────────────────────────────────────────────────
var droneGeo = new THREE.SphereGeometry(7, 14, 10);
var drones3d = [];

for (var i = 0; i < N_DRONES; i++) {{
  var col = COLORS[i % COLORS.length];

  var mat  = new THREE.MeshPhongMaterial({{
    color: col,
    emissive: col,
    emissiveIntensity: 0.35,
  }});
  var mesh = new THREE.Mesh(droneGeo, mat);
  mesh.position.set(AREA / 2, AREA / 2, 80);
  scene.add(mesh);

  // Trail line
  var trailMat  = new THREE.LineBasicMaterial({{
    color: col, opacity: 0.45, transparent: true,
  }});
  var trailGeo  = new THREE.BufferGeometry();
  var trailLine = new THREE.Line(trailGeo, trailMat);
  scene.add(trailLine);

  // Cellular link (drone → base station)
  var cellGeo  = new THREE.BufferGeometry();
  var cellLine = new THREE.Line(
    cellGeo,
    new THREE.LineBasicMaterial({{ color: 0x4488ff, opacity: 0.45,
                                    transparent: true }})
  );
  scene.add(cellLine);

  drones3d.push({{
    mesh:     mesh,
    trailLine: trailLine,
    trailPts:  [],
    target:   new THREE.Vector3(AREA / 2, AREA / 2, 80),
    cellLine: cellLine,
  }});
}}

// ── Obstacle pool ─────────────────────────────────────────────────────────────
var obsMeshes = {{}};   // index → THREE.Mesh

function updateObstacles(obsArr) {{
  // Remove stale
  var keep = {{}};
  for (var k = 0; k < obsArr.length; k++) keep[k] = true;
  for (var ek in obsMeshes) {{
    if (!keep[ek]) {{
      scene.remove(obsMeshes[ek]);
      obsMeshes[ek].geometry.dispose();
      delete obsMeshes[ek];
    }}
  }}
  // Add / reposition
  for (var oi = 0; oi < obsArr.length; oi++) {{
    var o = obsArr[oi];
    var r = o.radius || 15;
    if (!obsMeshes[oi]) {{
      var geo = new THREE.SphereGeometry(r, 10, 8);
      var mat = new THREE.MeshPhongMaterial({{
        color: 0xff4444,
        transparent: true,
        opacity: 0.45,
        emissive: 0x660000,
        emissiveIntensity: 0.3,
      }});
      obsMeshes[oi] = new THREE.Mesh(geo, mat);
      scene.add(obsMeshes[oi]);
    }}
    obsMeshes[oi].position.set(o.pos[0], o.pos[1], o.pos[2]);
  }}
}}

// ── RF D2D link pool ──────────────────────────────────────────────────────────
var rfLines = [];

function updateRFLinks(drones, rfPairs) {{
  // Dispose old
  rfLines.forEach(function(l) {{
    scene.remove(l);
    l.geometry.dispose();
  }});
  rfLines = [];

  (rfPairs || []).forEach(function(p) {{
    var a = drones[p[0]], b = drones[p[1]];
    if (!a || !b) return;
    var pts = [
      new THREE.Vector3(a.pos[0], a.pos[1], a.pos[2]),
      new THREE.Vector3(b.pos[0], b.pos[1], b.pos[2]),
    ];
    var geo  = new THREE.BufferGeometry().setFromPoints(pts);
    var line = new THREE.Line(
      geo,
      new THREE.LineBasicMaterial({{ color: 0x33ff77, opacity: 0.75,
                                      transparent: true }})
    );
    scene.add(line);
    rfLines.push(line);
  }});
}}

// ── HUD ───────────────────────────────────────────────────────────────────────
var hud3 = document.getElementById('hud3');

function updateHUD(msg) {{
  var s = msg.summary || {{}};
  hud3.innerHTML =
    't = ' + (msg.time_s || 0).toFixed(1) + ' s' +
    ' &nbsp;|&nbsp; Obs: '     + (s.total_obstacles  || 0) +
    ' &nbsp;|&nbsp; Arrived: ' + (s.arrived           || 0) + '/' + N_DRONES +
    ' &nbsp;|&nbsp; Cell OK: ' + (s.active_cellular   || 0) + '/' + N_DRONES +
    ' &nbsp;|&nbsp; RF: '      + (s.active_rf_links   || 0) +
    ' &nbsp;|&nbsp; Thr: '     + (s.avg_throughput_mbps || 0).toFixed(2) + ' Mbps';
}}

// ── Resize handling ───────────────────────────────────────────────────────────
window.addEventListener('resize', function() {{
  var w = canvas.clientWidth;
  var h = {height};
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}});

// ── WebSocket ─────────────────────────────────────────────────────────────────
var latestFrame = null;

function connect() {{
  var ws = new WebSocket(WS_URL);
  hud3.textContent = 'connecting…';

  ws.onopen  = function() {{ hud3.textContent = '● live'; }};
  ws.onerror = function() {{ ws.close(); }};
  ws.onclose = function() {{
    hud3.textContent = '○ reconnecting…';
    setTimeout(connect, 2500);
  }};
  ws.onmessage = function(evt) {{
    var msg = JSON.parse(evt.data);
    if (msg.type === 'done') {{
      hud3.textContent = '✓ simulation complete — ' + msg.total_frames + ' frames';
      ws.close();
      return;
    }}
    latestFrame = msg;
  }};
}}

connect();

// ── Render loop ───────────────────────────────────────────────────────────────
var bsVec = new THREE.Vector3(BS_POS[0], BS_POS[1], BS_POS[2]);

function animate() {{
  requestAnimationFrame(animate);
  controls.update();

  if (latestFrame) {{
    var drones = latestFrame.drones    || [];
    var obs    = latestFrame.obstacles || [];
    var summ   = latestFrame.summary   || {{}};

    drones.forEach(function(d, i) {{
      if (i >= N_DRONES) return;
      var dr = drones3d[i];

      // Update lerp target from new frame
      dr.target.set(d.pos[0], d.pos[1], d.pos[2]);

      // Trail — append current (pre-lerp) mesh position
      var cur = dr.mesh.position.clone();
      dr.trailPts.push(cur);
      if (dr.trailPts.length > TRAIL_LEN)
        dr.trailPts = dr.trailPts.slice(-TRAIL_LEN);
      if (dr.trailPts.length >= 2)
        dr.trailLine.geometry.setFromPoints(dr.trailPts);

      // Cellular link colour
      dr.cellLine.material.color.set(d.cellular_ok ? 0x4488ff : 0xff4444);
      dr.cellLine.geometry.setFromPoints([dr.mesh.position.clone(), bsVec]);
    }});

    updateObstacles(obs);
    updateRFLinks(drones, summ.rf_pairs);
    updateHUD(latestFrame);

    latestFrame = null;   // consumed; next frame will update again
  }}

  // Lerp drone meshes every animation frame → smooth motion at ~60 fps
  drones3d.forEach(function(dr) {{
    dr.mesh.position.lerp(dr.target, 0.18);
  }});

  renderer.render(scene, camera);
}}

animate();
</script>
</body>
</html>"""


def render_swarm_3d_view(
    ws_url:       str,
    drone_colors: list[str],   # CSS hex strings e.g. "#e74c3c"
    n_drones:     int,
    area:         float = 1000.0,
    bs_pos:       list[float] = None,
    height:       int   = 520,
) -> None:
    """
    Embed the Three.js live 3D WebSocket component.

    Parameters
    ----------
    ws_url       : Full ws:// WebSocket URL for the obstacle stream.
    drone_colors : CSS hex colour per drone (e.g. ["#e74c3c", "#3498db"]).
    n_drones     : Number of drones to initialise.
    area         : Simulation XY extent in metres (default 1000).
    bs_pos       : Base-station [x, y, z] in sim metres (default [500, 500, 0]).
    height       : Component height in pixels.
    """
    if bs_pos is None:
        bs_pos = [500.0, 500.0, 0.0]

    # Convert CSS hex → integer (Three.js expects 0xRRGGBB integers)
    int_colors = [int(c.lstrip("#"), 16) for c in drone_colors]

    html = _TEMPLATE.format(
        ws_url   = ws_url,
        colors   = json.dumps(int_colors),
        n_drones = n_drones,
        area     = area,
        bs_pos   = json.dumps(bs_pos),
        height   = height,
    )
    components.html(html, height=height + 20)
