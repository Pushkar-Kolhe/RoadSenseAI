// RoadSense AI dashboard. Plain JavaScript + Leaflet.
const COLORS = { High: "#dc2626", Medium: "#d97706", Low: "#16a34a" };
const map = L.map("map").setView([18.516, 73.784], 14);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const markers = {};          // id -> Leaflet marker
let layer = L.layerGroup().addTo(map);
let knownIds = null;         // set of ids seen so far (to detect NEW defects)
let firstFit = true;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function popupHtml(d) {
  const sim = d.source === "simulated" ? '<span class="sim">SIMULATED</span>' : "";
  const vib = d.vibration_g != null ? d.vibration_g.toFixed(2) + " g" : "no sensor data";
  const img = d.evidence_url ? `<img src="${esc(d.evidence_url)}" alt="evidence">` : "";
  const opts = ["Reported", "In Progress", "Repaired"]
    .map((s) => `<option ${s === d.status ? "selected" : ""}>${s}</option>`).join("");
  return `<div class="popup">
    <b>#${d.id} ${esc(d.defect_type)}</b> <span class="badge ${esc(d.severity)}">${esc(d.severity)}</span>${sim}<br>
    Confidence: ${(d.confidence * 100).toFixed(0)}%<br>
    Verification: ${esc(d.verification)}<br>
    Vibration: ${vib}<br>
    First seen: ${esc(d.detected_at)} UTC<br>
    Seen ${d.detection_count}x<br>
    Status: <select onchange="setStatus(${d.id}, this.value)">${opts}</select>
    ${img}</div>`;
}

async function setStatus(id, status) {
  await fetch(`/api/defects/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  load();
}

function notifyNew(count) {
  document.title = `(${count} new) RoadSense AI Dashboard`;
  setTimeout(() => (document.title = "RoadSense AI Dashboard"), 4000);
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification("RoadSense AI", { body: `${count} new road defect(s) recorded` });
  }
}

async function load() {
  const q = new URLSearchParams();
  for (const [key, el] of [["severity", "f-severity"], ["status", "f-status"], ["source", "f-source"], ["sort", "f-sort"]]) {
    if ($(el).value) q.set(key, $(el).value);
  }
  const [defects, stats] = await Promise.all([
    fetch("/api/defects?" + q).then((r) => r.json()),
    fetch("/api/stats").then((r) => r.json()),
  ]);

  $("s-total").textContent = stats.total;
  $("s-high").textContent = stats.by_severity.High || 0;
  $("s-med").textContent = stats.by_severity.Medium || 0;
  $("s-low").textContent = stats.by_severity.Low || 0;

  layer.clearLayers();
  const tbody = $("rows");
  tbody.innerHTML = "";
  const bounds = [];
  for (const d of defects) {
    if (d.latitude != null) {
      const m = L.circleMarker([d.latitude, d.longitude], {
        radius: 9, color: "#fff", weight: 2, fillColor: COLORS[d.severity], fillOpacity: 0.9,
      }).bindPopup(popupHtml(d));
      m.addTo(layer);
      markers[d.id] = m;
      bounds.push([d.latitude, d.longitude]);
    }
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${d.id}${d.source === "simulated" ? '<span class="sim">SIM</span>' : ""}</td>
      <td><span class="badge ${esc(d.severity)}">${esc(d.severity)}</span></td>
      <td>${esc(d.status)}</td><td>${esc(d.detected_at.replace("T", " "))}</td><td>${d.detection_count}x</td>`;
    tr.onclick = () => {
      const m = markers[d.id];
      if (m) { map.setView(m.getLatLng(), 17); m.openPopup(); }
    };
    tbody.appendChild(tr);
  }
  $("empty").hidden = defects.length > 0;
  if (firstFit && bounds.length) { map.fitBounds(bounds, { padding: [40, 40] }); firstFit = false; }

  // detect brand-new defects since last refresh
  const ids = new Set(defects.map((d) => d.id));
  if (knownIds !== null) {
    const added = [...ids].filter((i) => !knownIds.has(i)).length;
    if (added > 0) notifyNew(added);
  }
  knownIds = ids;
}

for (const id of ["f-severity", "f-status", "f-source", "f-sort"]) $(id).onchange = () => { knownIds = null; load(); };
if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
load();
setInterval(load, 5000);
