/* ==========================================================================
   RMMV Dashboard — Leaflet Map Utilities
   ========================================================================== */

/**
 * Status-to-color mapping for project markers.
 */
const STATUS_COLORS = {
  active:    '#00b894',
  delayed:   '#fdcb6e',
  critical:  '#d63031',
  completed: '#0984e3'
};

/**
 * Initialise the main GIS map with project circle markers.
 *
 * @param {string}  elementId  – DOM id of the map container div
 * @param {Array}   projects   – Array of project objects, each containing:
 *        { lat, lng, name, status, physical_progress, financial_progress, ulb_name }
 * @param {Object}  [options]  – Optional overrides:
 *        { center: [lat, lng], zoom: Number, tileUrl: String }
 * @returns {L.Map} The Leaflet map instance
 */
function initMap(elementId, projects, options) {
  'use strict';

  var defaults = {
    center: [11.1271, 78.6569],   // Tamil Nadu centre
    zoom: 7,
    tileUrl: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    tileAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  };

  var cfg = Object.assign({}, defaults, options || {});

  var map = L.map(elementId, {
    center: cfg.center,
    zoom: cfg.zoom,
    scrollWheelZoom: true,
    zoomControl: true
  });

  L.tileLayer(cfg.tileUrl, {
    attribution: cfg.tileAttribution,
    maxZoom: 18
  }).addTo(map);

  if (!projects || projects.length === 0) {
    return map;
  }

  var markers = [];

  projects.forEach(function (p) {
    if (p.lat == null || p.lng == null) return;

    var color  = STATUS_COLORS[p.status] || '#6c757d';
    var physical = p.physical_progress || 0;
    var financial = p.financial_progress || 0;
    var statusLabel = (p.status || 'unknown').charAt(0).toUpperCase() + (p.status || 'unknown').slice(1);

    var badgeClass = 'badge-' + (p.status || 'draft');

    var popupHtml =
      '<div class="map-popup-card" style="min-width:200px">' +
        '<div class="popup-title">' + escapeHtml(p.name) + '</div>' +
        '<div class="popup-ulb"><i class="bi bi-building"></i> ' + escapeHtml(p.ulb_name || '') + '</div>' +
        '<div class="popup-progress">' +
          '<div class="popup-progress-label">Physical Progress — ' + physical.toFixed(1) + '%</div>' +
          '<div class="popup-progress-bar">' +
            '<div class="fill" style="width:' + physical + '%;background:' + color + '"></div>' +
          '</div>' +
        '</div>' +
        '<div class="popup-progress">' +
          '<div class="popup-progress-label">Financial Progress — ' + financial.toFixed(1) + '%</div>' +
          '<div class="popup-progress-bar">' +
            '<div class="fill" style="width:' + financial + '%;background:#0a192f"></div>' +
          '</div>' +
        '</div>' +
        '<div style="margin-top:8px"><span class="badge-status ' + badgeClass + '">' + statusLabel + '</span></div>' +
      '</div>';

    var marker = L.circleMarker([p.lat, p.lng], {
      radius: 9,
      fillColor: color,
      color: '#fff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85
    }).addTo(map);

    marker.bindPopup(popupHtml, { maxWidth: 260 });
    markers.push(marker);
  });

  // Fit map bounds to markers
  if (markers.length > 0) {
    var group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.15));
  }

  // Force a resize recalculation after the map is in the DOM
  setTimeout(function () { map.invalidateSize(); }, 250);

  return map;
}


/**
 * Initialise a small draggable-marker map for GPS location picking.
 * Updates hidden inputs whose ids are passed via latInputId / lngInputId.
 *
 * @param {string} elementId  – DOM id of the mini-map div
 * @param {number} lat        – Initial latitude  (default: MP centre)
 * @param {number} lng        – Initial longitude  (default: MP centre)
 * @param {string} latInputId – id of the hidden lat input (default 'id_latitude')
 * @param {string} lngInputId – id of the hidden lng input (default 'id_longitude')
 * @returns {{ map: L.Map, marker: L.Marker }}
 */
function initMiniMap(elementId, lat, lng, latInputId, lngInputId) {
  'use strict';

  lat = lat || 11.1271;
  lng = lng || 78.6569;
  latInputId = latInputId || 'id_latitude';
  lngInputId = lngInputId || 'id_longitude';

  var map = L.map(elementId, {
    center: [lat, lng],
    zoom: 14,
    scrollWheelZoom: true,
    zoomControl: true
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap',
    maxZoom: 19
  }).addTo(map);

  var marker = L.marker([lat, lng], { draggable: true }).addTo(map);

  function syncInputs(latlng) {
    var latEl = document.getElementById(latInputId);
    var lngEl = document.getElementById(lngInputId);
    if (latEl) latEl.value = latlng.lat.toFixed(6);
    if (lngEl) lngEl.value = latlng.lng.toFixed(6);
  }

  // Set initial values
  syncInputs({ lat: lat, lng: lng });

  // Update on drag
  marker.on('dragend', function (e) {
    syncInputs(e.target.getLatLng());
  });

  // Update on map click
  map.on('click', function (e) {
    marker.setLatLng(e.latlng);
    syncInputs(e.latlng);
  });

  setTimeout(function () { map.invalidateSize(); }, 250);

  return { map: map, marker: marker };
}


/**
 * Capture the user's GPS coordinates via the browser Geolocation API.
 * On success, updates the readonly lat/lng inputs and re-centres the mini map.
 *
 * @param {string} latInputId
 * @param {string} lngInputId
 * @param {Object} [miniMapRef] – Object returned by initMiniMap (has .map and .marker)
 */
function captureGPS(latInputId, lngInputId, miniMapRef) {
  'use strict';

  latInputId = latInputId || 'id_latitude';
  lngInputId = lngInputId || 'id_longitude';

  if (!navigator.geolocation) {
    alert('Geolocation is not supported by your browser.');
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function (position) {
      var lat = position.coords.latitude;
      var lng = position.coords.longitude;

      var latEl = document.getElementById(latInputId);
      var lngEl = document.getElementById(lngInputId);
      if (latEl) latEl.value = lat.toFixed(6);
      if (lngEl) lngEl.value = lng.toFixed(6);

      if (miniMapRef && miniMapRef.map && miniMapRef.marker) {
        miniMapRef.marker.setLatLng([lat, lng]);
        miniMapRef.map.setView([lat, lng], 16);
      }
    },
    function (err) {
      alert('Unable to retrieve location: ' + err.message);
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}


/* --------------------------------------------------------------------------
   Utility: basic HTML escaping
   -------------------------------------------------------------------------- */
function escapeHtml(str) {
  if (!str) return '';
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
