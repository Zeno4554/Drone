import re
import os

html_path = r'd:\Drone\frontend\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add Three.js to <head>
if 'three.min.js' not in html:
    head_injection = """
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js"></script>
"""
    html = html.replace('</head>', head_injection + '</head>')

# 2. Add Swarm tab to nav
nav_injection = """      <div class="nav-tab" data-tab="fleet" onclick="switchTab('fleet',this)">Fleet</div>
      <div class="nav-tab" data-tab="swarm" onclick="switchTab('swarm',this)">Swarm</div>"""
if 'data-tab="swarm"' not in html:
    html = html.replace('      <div class="nav-tab" data-tab="fleet" onclick="switchTab(\'fleet\',this)">Fleet</div>', nav_injection)

# 3. Add Swarm HTML content
if 'id="tab-swarm"' not in html:
    swarm_html = """
  <!-- ══════ SWARM MISSION ══════ -->
  <div class="content" id="tab-swarm">
    <div class="page-header">
      <h1 data-text="Swarm Mission">Swarm Mission</h1>
      <p>// 3d drone simulation &middot; real-time collision avoidance &middot; dynamic routing</p>
    </div>
    
    <div id="swarm-setup-view" style="display:flex;gap:20px;">
      <div class="card" style="flex:0 0 320px">
        <div class="card-header"><div class="card-title"><div class="icon">&#x2699;</div> Setup</div></div>
        <div class="form-row"><label>Number of Drones (1-6)</label><input type="number" id="sm-drones" value="3" min="1" max="6" onchange="initSwarmSetupMap()"></div>
        <div class="form-row"><label>Speed (m/s)</label><input type="number" id="sm-speed" value="15" min="5" max="30"></div>
        <div class="form-row"><label>Sensors</label>
          <div style="font-size:12px;display:flex;gap:10px;margin-top:6px;color:var(--text2)">
            <label><input type="checkbox" id="sm-us" checked> Ultrasonic</label>
            <label><input type="checkbox" id="sm-lidar" checked> LiDAR</label>
            <label><input type="checkbox" id="sm-radar" checked> Radar</label>
          </div>
        </div>
        <div class="form-row"><label>Obstacles Count</label><input type="number" id="sm-obs-count" value="8" min="0" max="20"></div>
        <div class="form-row"><label>Simulation Duration (s)</label><input type="number" id="sm-duration" value="120" min="30" max="300"></div>
        <div class="form-row"><label>FPS</label><select id="sm-fps"><option value="5">5</option><option value="10">10</option><option value="20" selected>20</option></select></div>
        <button class="btn btn-primary" style="width:100%;margin-top:16px" id="btn-launch-swarm" onclick="launchSwarm()"><span class="btn-label">Launch Mission</span><div class="spinner"></div></button>
      </div>
      <div class="card" style="flex:1;position:relative;padding:0;overflow:hidden">
        <div id="swarm-setup-map" style="width:100%;height:100%;min-height:500px;border-radius:12px"></div>
        <div style="position:absolute;top:16px;left:50%;transform:translateX(-50%);z-index:900;background:rgba(0,229,255,0.15);border:1px solid var(--accent);backdrop-filter:blur(8px);padding:8px 16px;border-radius:20px;font-size:13px;font-family:var(--mono);color:var(--accent)" id="swarm-instruction">Click map to place D1 Start &#x25b2;</div>
      </div>
    </div>

    <div id="swarm-running-view" style="display:none;flex-direction:column;gap:20px">
      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button class="btn btn-danger" onclick="stopSwarm()">&#x23f9; Stop &amp; New Mission</button>
        <button class="btn" style="background:var(--surface2);border:1px solid var(--border);color:var(--text)" onclick="resetSwarm()">&#x21bb; Reset Run</button>
      </div>
      <div style="display:flex;gap:20px;height:540px">
        <div class="card" style="flex:11;padding:0;overflow:hidden;position:relative">
           <div id="swarm-live-map" style="width:100%;height:100%;border-radius:12px;z-index:1"></div>
           <div id="swarm-hud-2d" class="map-hud" style="left:16px;right:auto;bottom:16px;top:auto;z-index:900"></div>
        </div>
        <div class="card" style="flex:9;padding:0;overflow:hidden;position:relative">
           <canvas id="swarm-3d-canvas" style="width:100%;height:100%;display:block;border-radius:12px"></canvas>
           <div id="swarm-hud-3d" class="map-hud" style="left:16px;right:auto;bottom:16px;top:auto;z-index:900"></div>
        </div>
      </div>
    </div>
  </div>
"""
    html = html.replace('</div>\n\n<!-- EMERGENCY MODAL -->', swarm_html + '\n</div>\n\n<!-- EMERGENCY MODAL -->')

js_logic = """
/* ═══════════════════════════════════════════════
   SWARM MISSION LOGIC
   ═══════════════════════════════════════════════ */
const SWARM_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"];
let setupMap = null;
let setupMarkers = [];
let setupLines = [];
let dronePoints = []; // [{start: [lat, lon], end: [lat, lon]}]
let clickTarget = 0;

let swarmSessionId = null;
let swarmWs = null;
let liveMap2D = null;
let liveMarkers2D = {};
let liveTrails2D = {};
let liveSensors2D = {};
let liveObs2D = {};
let liveCellLinks2D = [];
let liveRFLinks2D = {};
let refLat = 13.0160;
let refLon = 77.5700;

let swarm3D = {
  scene: null, camera: null, renderer: null, controls: null,
  drones: [], obs: {}, rfLines: [], bsMesh: null, animating: false
};

// Hook switchTab
const origSwitchTab = switchTab;
switchTab = function(name, el) {
  origSwitchTab(name, el);
  if (name === 'swarm' && !setupMap) {
    setTimeout(initSwarmSetupMap, 200);
  }
};

function initSwarmSetupMap() {
  const nDrones = parseInt(document.getElementById('sm-drones').value) || 3;
  
  if (!setupMap) {
    setupMap = L.map('swarm-setup-map', {scrollWheelZoom:true, zoomControl:false}).setView([13.0160, 77.5700], 13);
    L.control.zoom({position:'topright'}).addTo(setupMap);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {maxZoom:19}).addTo(setupMap);
    
    setupMap.on('click', function(e) { handleSetupClick(e.latlng.lat, e.latlng.lng); });
  }
  
  if (dronePoints.length > nDrones) {
    dronePoints = dronePoints.slice(0, nDrones);
  } else {
    while (dronePoints.length < nDrones) dronePoints.push({start: null, end: null});
  }
  
  clickTarget = dronePoints.findIndex(d => !d.start || !d.end) * 2;
  if (clickTarget < 0) clickTarget = nDrones * 2;
  else if (dronePoints[Math.floor(clickTarget/2)].start) clickTarget += 1;
  
  updateSetupUI();
}

function handleSetupClick(lat, lng) {
  const nDrones = parseInt(document.getElementById('sm-drones').value) || 3;
  if (clickTarget >= nDrones * 2) return;
  
  const dIdx = Math.floor(clickTarget / 2);
  const isStart = clickTarget % 2 === 0;
  
  if (isStart) dronePoints[dIdx].start = [lat, lng];
  else dronePoints[dIdx].end = [lat, lng];
  
  let newTarget = -1;
  for (let i = 0; i < nDrones; i++) {
    if (!dronePoints[i].start) { newTarget = i * 2; break; }
    if (!dronePoints[i].end) { newTarget = i * 2 + 1; break; }
  }
  
  if (newTarget === -1) {
    clickTarget = nDrones * 2;
  } else {
    clickTarget = newTarget;
  }
  
  updateSetupUI();
}

function updateSetupUI() {
  const nDrones = parseInt(document.getElementById('sm-drones').value) || 3;
  
  setupMarkers.forEach(m => setupMap.removeLayer(m));
  setupLines.forEach(l => setupMap.removeLayer(l));
  setupMarkers = []; setupLines = [];
  
  dronePoints.forEach((d, i) => {
    const col = SWARM_COLORS[i % SWARM_COLORS.length];
    if (d.start) {
      setupMarkers.push(L.circleMarker(d.start, {radius:7, color:col, fillColor:col, fillOpacity:0.9}).addTo(setupMap));
      setupMarkers.push(L.marker(d.start, {icon: L.divIcon({html: `<div style="font-size:10px;font-weight:bold;color:${col};text-shadow:0 0 3px #000">&#x25b2; D${i+1}</div>`, className: '', iconSize:[40,16], iconAnchor:[0,16]})}).addTo(setupMap));
    }
    if (d.end) {
      setupMarkers.push(L.circleMarker(d.end, {radius:7, color:col, fillColor:col, fillOpacity:0.5, dashArray:'6'}).addTo(setupMap));
      setupMarkers.push(L.marker(d.end, {icon: L.divIcon({html: `<div style="font-size:10px;font-weight:bold;color:${col};text-shadow:0 0 3px #000">&#x2715; D${i+1}</div>`, className: '', iconSize:[40,16], iconAnchor:[0,16]})}).addTo(setupMap));
    }
    if (d.start && d.end) {
      setupLines.push(L.polyline([d.start, d.end], {color:col, weight:1.5, dashArray:'6', opacity:0.55}).addTo(setupMap));
    }
  });
  
  const instr = document.getElementById('swarm-instruction');
  const btn = document.getElementById('btn-launch-swarm');
  
  if (clickTarget < nDrones * 2) {
    const dIdx = Math.floor(clickTarget / 2);
    const type = clickTarget % 2 === 0 ? 'Start &#x25b2;' : 'End &#x2715;';
    instr.innerHTML = `Click map to place D${dIdx+1} ${type}`;
    btn.disabled = true;
    btn.classList.remove('loading');
    btn.style.opacity = '0.5';
    btn.style.pointerEvents = 'none';
  } else {
    instr.innerHTML = `All points set &mdash; ready to launch`;
    btn.disabled = false;
    btn.removeAttribute('disabled');
    btn.classList.remove('loading');
    btn.style.opacity = '1';
    btn.style.pointerEvents = 'auto';
  }
}

async function launchSwarm() {
  const btn = document.getElementById('btn-launch-swarm');
  btn.classList.add('loading'); btn.disabled = true;
  
  const nDrones = parseInt(document.getElementById('sm-drones').value) || 3;
  if (clickTarget < nDrones * 2) {
    alert("Please set all Start and End points on the map before launching.");
    btn.classList.remove('loading'); btn.disabled = false;
    return;
  }
  
  const speed = parseFloat(document.getElementById('sm-speed').value);
  const starts = dronePoints.map(d => [d.start[0], d.start[1], 80.0]);
  const ends = dronePoints.map(d => [d.end[0], d.end[1], 80.0]);
  
  refLat = starts.reduce((s, d) => s + d[0], 0) / nDrones;
  refLon = starts.reduce((s, d) => s + d[1], 0) / nDrones;
  
  const payload = {
    n_drones: nDrones,
    start_points: starts,
    end_points: ends,
    speeds: Array(nDrones).fill(speed),
    active_sensors: { ultrasonic: document.getElementById('sm-us').checked, lidar: document.getElementById('sm-lidar').checked, radar: document.getElementById('sm-radar').checked },
    total_time_s: parseFloat(document.getElementById('sm-duration').value),
    fps: parseInt(document.getElementById('sm-fps').value),
    obs_count: parseInt(document.getElementById('sm-obs-count').value),
    obs_radius_min: 5.0, obs_radius_max: 30.0,
    ref_lat: refLat, ref_lon: refLon
  };
  
  try {
    const r = await fetch(`${API_BASE}/swarm/obstacles/start`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const res = await r.json();
    if (res.session_id) {
      swarmSessionId = res.session_id;
      document.getElementById('swarm-setup-view').style.display = 'none';
      document.getElementById('swarm-running-view').style.display = 'flex';
      initSwarmLiveMap2D();
      initSwarm3D();
      connectSwarmWS();
    }
  } catch (e) { alert('Failed to start swarm mission.'); }
  finally { btn.classList.remove('loading'); btn.disabled = false; }
}

async function stopSwarm() {
  if (swarmWs) { swarmWs.close(); swarmWs = null; }
  if (swarmSessionId) { try { await fetch(`${API_BASE}/swarm/obstacles/${swarmSessionId}`, {method:'DELETE'}); }catch(e){} }
  swarmSessionId = null;
  swarm3D.animating = false;
  document.getElementById('swarm-setup-view').style.display = 'flex';
  document.getElementById('swarm-running-view').style.display = 'none';
}

async function resetSwarm() {
  if (!swarmSessionId) return;
  try { await fetch(`${API_BASE}/swarm/obstacles/${swarmSessionId}/reset`, {method: 'POST'}); }catch(e){}
}

function bearingLatLon(fromLL, toLL) {
  const dLon = (toLL[1]-fromLL[1])*Math.PI/180, lat1 = fromLL[0]*Math.PI/180, lat2 = toLL[0]*Math.PI/180;
  return Math.atan2(Math.sin(dLon)*Math.cos(lat2), Math.cos(lat1)*Math.sin(lat2)-Math.sin(lat1)*Math.cos(lat2)*Math.cos(dLon));
}

function offsetLatLon(ll, distM, brgRad) {
  const R=6371000, lat1=ll[0]*Math.PI/180, lon1=ll[1]*Math.PI/180;
  const lat2 = Math.asin(Math.sin(lat1)*Math.cos(distM/R) + Math.cos(lat1)*Math.sin(distM/R)*Math.cos(brgRad));
  const lon2 = lon1 + Math.atan2(Math.sin(brgRad)*Math.sin(distM/R)*Math.cos(lat1), Math.cos(distM/R)-Math.sin(lat1)*Math.sin(lat2));
  return [lat2*180/Math.PI, lon2*180/Math.PI];
}

function initSwarmLiveMap2D() {
  if (liveMap2D) liveMap2D.remove();
  liveMap2D = L.map('swarm-live-map', {scrollWheelZoom:true, zoomControl:false}).setView([refLat, refLon], 14);
  L.control.zoom({position:'topright'}).addTo(liveMap2D);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {maxZoom:19}).addTo(liveMap2D);
  
  liveMarkers2D = {}; liveTrails2D = {}; liveSensors2D = {};
  liveObs2D = {}; liveCellLinks2D = []; liveRFLinks2D = {};
  
  const bsLL = [refLat + 500/111320, refLon + 500/(111320*Math.cos(refLat*Math.PI/180))];
  L.circleMarker(bsLL, {radius:8, color:'#ff4444', fillColor:'#ff4444', fillOpacity:0.8}).addTo(liveMap2D).bindTooltip('gNB');
  
  dronePoints.forEach((d, i) => {
    const c = SWARM_COLORS[i % SWARM_COLORS.length];
    L.circleMarker(d.start, {radius:6, color:c, fillColor:c, fillOpacity:0.9, weight:2}).addTo(liveMap2D);
    L.circleMarker(d.end, {radius:6, color:c, fillColor:'transparent', fillOpacity:0, weight:2, dashArray:'5'}).addTo(liveMap2D);
    liveMarkers2D[i] = L.circleMarker(d.start, {radius:7, color:c, fillColor:c, fillOpacity:0.95, weight:2}).addTo(liveMap2D);
    liveTrails2D[i] = { history: [], line: L.polyline([], {color:c, weight:1.5, opacity:0.45}).addTo(liveMap2D) };
    liveCellLinks2D[i] = L.polyline([], {color:'#4488ff', weight:1.2, dashArray:'6', opacity:0.7}).addTo(liveMap2D);
    liveSensors2D[i] = {
      us: L.polyline([], {color:'#ffdd00', weight:2.2, opacity:0.9}).addTo(liveMap2D),
      radar: L.circle([0,0], {radius:1, color:'#4488ff', weight:1, fillOpacity:0, opacity:0.22}).addTo(liveMap2D),
      lidar: Array(24).fill(0).map(()=> L.polyline([], {color:'#33ff77', weight:0.7, opacity:0.5}).addTo(liveMap2D))
    };
  });
}

function initSwarm3D() {
  const canvas = document.getElementById('swarm-3d-canvas');
  if (swarm3D.renderer) { swarm3D.renderer.dispose(); }
  
  swarm3D.renderer = new THREE.WebGLRenderer({canvas: canvas, antialias: true});
  swarm3D.renderer.setPixelRatio(window.devicePixelRatio);
  swarm3D.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
  swarm3D.renderer.setClearColor(0x0b111c);
  
  swarm3D.scene = new THREE.Scene();
  swarm3D.camera = new THREE.PerspectiveCamera(50, canvas.clientWidth/canvas.clientHeight, 1, 8000);
  swarm3D.camera.position.set(1400, -500, 700);
  swarm3D.camera.up.set(0, 0, 1);
  
  swarm3D.controls = new THREE.OrbitControls(swarm3D.camera, swarm3D.renderer.domElement);
  swarm3D.controls.target.set(500, 500, 80);
  swarm3D.controls.enableDamping = true;
  swarm3D.controls.dampingFactor = 0.08;
  
  swarm3D.scene.add(new THREE.AmbientLight(0x334466, 3));
  const dl = new THREE.DirectionalLight(0xffffff, 1.2); dl.position.set(1000, 1000, 800);
  swarm3D.scene.add(dl);
  
  const grid = new THREE.GridHelper(1000, 20, 0x1e3050, 0x1e3050);
  grid.rotation.x = Math.PI/2; grid.position.set(500, 500, 0);
  swarm3D.scene.add(grid);
  
  swarm3D.bsMesh = new THREE.Mesh(new THREE.OctahedronGeometry(16, 0), new THREE.MeshPhongMaterial({color: 0xff4444, emissive: 0xff2222, emissiveIntensity: 0.6}));
  swarm3D.bsMesh.position.set(500, 500, 0);
  swarm3D.scene.add(swarm3D.bsMesh);
  
  swarm3D.drones = [];
  const geo = new THREE.SphereGeometry(7, 14, 10);
  dronePoints.forEach((d, i) => {
    const col = parseInt(SWARM_COLORS[i % SWARM_COLORS.length].replace('#','0x'));
    const mesh = new THREE.Mesh(geo, new THREE.MeshPhongMaterial({color: col, emissive: col, emissiveIntensity: 0.35}));
    swarm3D.scene.add(mesh);
    const tl = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({color: col, opacity: 0.45, transparent: true}));
    swarm3D.scene.add(tl);
    const cl = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({color: 0x4488ff, opacity: 0.45, transparent: true}));
    swarm3D.scene.add(cl);
    swarm3D.drones.push({ mesh: mesh, trailLine: tl, trailPts: [], target: new THREE.Vector3(500, 500, 80), cellLine: cl });
  });
  
  swarm3D.obs = {};
  swarm3D.rfLines = [];
  
  if (!swarm3D.animating) {
    swarm3D.animating = true;
    requestAnimationFrame(animate3D);
  }
}

function animate3D() {
  if (!swarm3D.animating) return;
  requestAnimationFrame(animate3D);
  if (swarm3D.controls) swarm3D.controls.update();
  swarm3D.drones.forEach(dr => { dr.mesh.position.lerp(dr.target, 0.18); });
  if (swarm3D.renderer) swarm3D.renderer.render(swarm3D.scene, swarm3D.camera);
}

function connectSwarmWS() {
  const wsUrl = API_BASE.replace('http','ws') + '/swarm/obstacles/' + swarmSessionId + '/stream';
  swarmWs = new WebSocket(wsUrl);
  
  swarmWs.onmessage = function(e) {
    const msg = JSON.parse(e.data);
    if (msg.type === 'done') {
      document.getElementById('swarm-hud-2d').innerHTML = '✓ Simulation Complete';
      document.getElementById('swarm-hud-3d').innerHTML = '✓ Simulation Complete';
      return;
    }
    
    const bsLL = [refLat + 500/111320, refLon + 500/(111320*Math.cos(refLat*Math.PI/180))];
    const bsVec = new THREE.Vector3(500, 500, 0);
    
    // Drones
    (msg.drones||[]).forEach((d, i) => {
      if (i >= dronePoints.length) return;
      const ll = d.pos_ll ? [d.pos_ll[0], d.pos_ll[1]] : [refLat + d.pos[1]/111320, refLon + d.pos[0]/(111320*Math.cos(refLat*Math.PI/180))];
      
      // 2D
      liveMarkers2D[i].setLatLng(ll);
      liveTrails2D[i].history.push(ll);
      if (liveTrails2D[i].history.length > 40) liveTrails2D[i].history.shift();
      liveTrails2D[i].line.setLatLngs(liveTrails2D[i].history);
      
      liveCellLinks2D[i].setLatLngs([ll, bsLL]).setStyle({color: d.cellular_ok ? '#4488ff' : '#ff4444', dashArray: d.cellular_ok ? '6' : '3'});
      
      const s2d = liveSensors2D[i];
      if (d.sensors && d.sensors.ultrasonic_m != null) {
        const hist = liveTrails2D[i].history;
        const angle = hist.length >= 2 ? bearingLatLon(hist[hist.length-2], ll) : 0;
        s2d.us.setLatLngs([ll, offsetLatLon(ll, d.sensors.ultrasonic_m, angle)]);
      } else { s2d.us.setLatLngs([]); }
      
      if (d.sensors && d.sensors.lidar_rays_m) {
        d.sensors.lidar_rays_m.forEach((dist, ri) => s2d.lidar[ri].setLatLngs([ll, offsetLatLon(ll, dist, (2*Math.PI/24)*ri)]));
      }
      if (d.sensors && d.sensors.radar_range_m) { s2d.radar.setLatLng(ll).setRadius(d.sensors.radar_range_m); }
      
      // 3D
      const dr3 = swarm3D.drones[i];
      dr3.target.set(d.pos[0], d.pos[1], d.pos[2]);
      dr3.trailPts.push(dr3.mesh.position.clone());
      if (dr3.trailPts.length > 60) dr3.trailPts.shift();
      if (dr3.trailPts.length >= 2) dr3.trailLine.geometry.setFromPoints(dr3.trailPts);
      dr3.cellLine.material.color.set(d.cellular_ok ? 0x4488ff : 0xff4444);
      dr3.cellLine.geometry.setFromPoints([dr3.mesh.position.clone(), bsVec]);
    });
    
    // RF Links
    const pairs = msg.summary.rf_pairs || [];
    for(let k in liveRFLinks2D) liveMap2D.removeLayer(liveRFLinks2D[k]);
    liveRFLinks2D = {};
    swarm3D.rfLines.forEach(l => { swarm3D.scene.remove(l); l.geometry.dispose(); });
    swarm3D.rfLines = [];
    
    pairs.forEach(p => {
      const a = p[0], b = p[1];
      if (a >= dronePoints.length || b >= dronePoints.length) return;
      liveRFLinks2D[`${a}-${b}`] = L.polyline([liveMarkers2D[a].getLatLng(), liveMarkers2D[b].getLatLng()], {color:'#33ff77', weight:1.8, opacity:0.75}).addTo(liveMap2D);
      const geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3((msg.drones[a]||{}).pos[0]||0, (msg.drones[a]||{}).pos[1]||0, (msg.drones[a]||{}).pos[2]||80),
        new THREE.Vector3((msg.drones[b]||{}).pos[0]||0, (msg.drones[b]||{}).pos[1]||0, (msg.drones[b]||{}).pos[2]||80)
      ]);
      const l3 = new THREE.Line(geo, new THREE.LineBasicMaterial({color: 0x33ff77, opacity: 0.75, transparent: true}));
      swarm3D.scene.add(l3); swarm3D.rfLines.push(l3);
    });
    
    // Obstacles
    const keep2D={}, keep3D={};
    (msg.obstacles||[]).forEach((o, oi) => {
      keep2D[oi]=true; keep3D[oi]=true;
      const rad = o.radius || 15;
      const ll = o.pos_ll ? [o.pos_ll[0], o.pos_ll[1]] : [refLat + o.pos[1]/111320, refLon + o.pos[0]/(111320*Math.cos(refLat*Math.PI/180))];
      
      if (!liveObs2D[oi]) liveObs2D[oi] = L.circle(ll, {radius:rad, color:'#ff4444', fillColor:'#ff4444', fillOpacity:0.3, weight:1.5}).addTo(liveMap2D);
      else liveObs2D[oi].setLatLng(ll).setRadius(rad);
      
      if (!swarm3D.obs[oi]) {
        swarm3D.obs[oi] = new THREE.Mesh(new THREE.SphereGeometry(rad, 10, 8), new THREE.MeshPhongMaterial({color: 0xff4444, transparent: true, opacity: 0.45, emissive: 0x660000, emissiveIntensity: 0.3}));
        swarm3D.scene.add(swarm3D.obs[oi]);
      }
      swarm3D.obs[oi].position.set(o.pos[0], o.pos[1], o.pos[2]);
    });
    for(let k in liveObs2D) { if(!keep2D[k]) { liveMap2D.removeLayer(liveObs2D[k]); delete liveObs2D[k]; } }
    for(let k in swarm3D.obs) { if(!keep3D[k]) { swarm3D.scene.remove(swarm3D.obs[k]); swarm3D.obs[k].geometry.dispose(); delete swarm3D.obs[k]; } }
    
    const summ = msg.summary || {};
    const hHTML = `t = ${(msg.time_s||0).toFixed(1)}s &nbsp;|&nbsp; Obs: ${summ.total_obstacles||0} &nbsp;|&nbsp; Arrived: ${summ.arrived||0}/${dronePoints.length} &nbsp;|&nbsp; Cell: ${summ.active_cellular||0} &nbsp;|&nbsp; RF: ${summ.active_rf_links||0}`;
    document.getElementById('swarm-hud-2d').innerHTML = hHTML;
    document.getElementById('swarm-hud-3d').innerHTML = hHTML;
  };
}
"""

if 'SWARM MISSION LOGIC' not in html:
    html = html.replace('</script>\n</body>', js_logic + '\n</script>\n</body>')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
