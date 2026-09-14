/*
  Leaflet.js + OpenStreetMap integration.

  initPickerMap(elementId, onPick) — shows a map the citizen can click on to
  drop a pin; calls onPick(lat, lng) whenever a pin is placed/moved.

  initViewMap(elementId, lat, lng, label) — shows a single read-only marker,
  used on the report detail page when a report has GPS coordinates.
*/

const DEFAULT_CENTER = [28.05, 81.6167]; // Nepalgunj, Nepal
const DEFAULT_ZOOM = 13;

function initPickerMap(elementId, onPick) {
  const map = L.map(elementId).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);

  let marker = null;

  map.on("click", (e) => {
    const { lat, lng } = e.latlng;
    if (marker) {
      marker.setLatLng(e.latlng);
    } else {
      marker = L.marker(e.latlng, { draggable: true }).addTo(map);
      marker.on("dragend", () => {
        const pos = marker.getLatLng();
        onPick(pos.lat, pos.lng);
      });
    }
    onPick(lat, lng);
  });

  return map;
}

function initViewMap(elementId, lat, lng, label) {
  const map = L.map(elementId).setView([lat, lng], 16);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);
  L.marker([lat, lng]).addTo(map).bindPopup(label || "Reported location");
  return map;
}
