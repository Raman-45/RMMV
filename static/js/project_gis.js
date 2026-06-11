/**
 * RMMV Dashboard — Project Digital Twin GIS Map
 * Handles rendering the per-project Leaflet map including boundaries,
 * assets, geotagged media, and progress overlays.
 */

/* global L, escapeHtml */

/**
 * Get construction status color
 * @param {string} status 
 * @returns {string} Hex color
 */
function getAssetStatusColor(status) {
    switch (status) {
        case 'not_started': return '#adb5bd';
        case 'excavation': return '#fdcb6e';
        case 'installation': return '#0984e3';
        case 'testing': return '#6c3483';
        case 'completed': return '#00b894';
        default: return '#adb5bd';
    }
}

/**
 * Get Bootstrap Icon class for asset type
 * @param {string} type 
 * @returns {string} CSS class
 */
function getAssetIcon(type) {
    switch (type) {
        case 'pipeline': return 'bi-water';
        case 'stp': return 'bi-funnel';
        case 'wtp': return 'bi-droplet-half';
        case 'oht': return 'bi-archive';
        case 'pump_house': return 'bi-gear-wide-connected';
        case 'valve': return 'bi-circle';
        case 'meter': return 'bi-speedometer';
        case 'manhole': return 'bi-circle-square';
        default: return 'bi-geo-alt';
    }
}

/**
 * Format string as title case
 */
function toTitleCase(str) {
    if (!str) return '';
    return str.replace(/_/g, ' ').replace(/\b\w/g, function(l){ return l.toUpperCase(); });
}

/**
 * Create styled popup HTML for an asset
 */
function createAssetPopup(asset) {
    var statusLabel = toTitleCase(asset.status);
    var typeLabel = toTitleCase(asset.asset_type);
    var badgeClass = asset.status === 'not_started' ? 'badge-draft' : 
                     (asset.status === 'completed' ? 'badge-approved' : 
                     (asset.status === 'testing' ? 'badge-info' : 'badge-submitted'));
    
    var html = '<div class="map-popup-card" style="min-width:220px">';
    html += '<div class="popup-title">' + escapeHtml(asset.name) + '</div>';
    html += '<div class="popup-ulb"><i class="' + getAssetIcon(asset.asset_type) + '"></i> ' + escapeHtml(typeLabel) + '</div>';
    
    if (asset.properties) {
        html += '<div class="popup-properties mt-2">';
        for (var key in asset.properties) {
            if (asset.properties.hasOwnProperty(key)) {
                html += '<div style="font-size:12px;color:#6c757d;"><strong>' + escapeHtml(toTitleCase(key)) + ':</strong> ' + escapeHtml(asset.properties[key]) + '</div>';
            }
        }
        html += '</div>';
    }

    if (asset.description) {
        html += '<div style="font-size:12px;margin-top:5px;border-top:1px solid #eee;padding-top:5px;">' + escapeHtml(asset.description) + '</div>';
    }
    
    html += '<div style="margin-top:10px;"><span class="badge-status ' + badgeClass + '">' + statusLabel + '</span></div>';
    html += '</div>';
    return html;
}

/**
 * Create popup for media marker
 */
function createMediaPopup(media) {
    var html = '<div class="map-popup-card" style="width:240px;text-align:center;">';
    if (media.thumbnail) {
        html += '<img src="' + escapeHtml(media.thumbnail) + '" style="width:100%;height:auto;border-radius:6px;margin-bottom:8px;max-height:180px;object-fit:cover;">';
    }
    if (media.description) {
        html += '<div style="font-size:12px;margin-bottom:6px;text-align:left;line-height:1.4;">' + escapeHtml(media.description) + '</div>';
    }
    html += '<div style="font-size:11px;color:#6c757d;text-align:left;">';
    html += '<i class="bi bi-calendar3"></i> ' + escapeHtml(media.created_at);
    html += ' &nbsp;|&nbsp; <i class="bi bi-geo-alt"></i> ' + media.lat.toFixed(6) + ', ' + media.lng.toFixed(6);
    html += '</div>';
    html += '</div>';
    return html;
}

/**
 * Initialize the project Leaflet map
 * @param {string} elementId DOM element ID
 * @param {Object} projectData { lat, lng, name, project_id }
 * @param {Object} options Leaflet options
 */
function initProjectMap(elementId, projectData, options) {
    var center = [projectData.lat || 11.1271, projectData.lng || 78.6569];
    var zoom = options && options.zoom ? options.zoom : 14;

    var map = L.map(elementId, {
        center: center,
        zoom: zoom,
        scrollWheelZoom: true,
        zoomControl: true
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19
    }).addTo(map);

    return map;
}

/**
 * Fetch and render GIS data for the project
 * @param {L.Map} map 
 * @param {number} projectId 
 * @param {string} apiUrl 
 */
function loadProjectGIS(map, projectId, apiUrl) {
    var boundaryLayer = L.layerGroup();
    var assetsLayer = L.layerGroup();
    var mediaLayer = L.layerGroup();
    var progressLayer = L.layerGroup();
    
    var mapBounds = L.latLngBounds();
    var hasBounds = false;

    // Fetch data
    fetch(apiUrl)
        .then(function(res) {
            if (!res.ok) throw new Error("Network error");
            return res.json();
        })
        .then(function(data) {
            // 1. Render Boundary
            if (data.boundary) {
                var boundaryStyle = {
                    color: '#0984e3',
                    weight: 2,
                    dashArray: '5, 5',
                    fillColor: '#0984e3',
                    fillOpacity: 0.1
                };
                var boundaryGeoJson = L.geoJSON(data.boundary, { style: boundaryStyle });
                boundaryGeoJson.addTo(boundaryLayer);
                
                var bounds = boundaryGeoJson.getBounds();
                if (bounds.isValid()) {
                    mapBounds.extend(bounds);
                    hasBounds = true;
                }
            }

            // 2. Render Assets & Progress Overlay
            if (data.assets && data.assets.length > 0) {
                data.assets.forEach(function(asset) {
                    if (!asset.geojson) return;
                    
                    var color = getAssetStatusColor(asset.status);
                    
                    // Create base asset geojson (standard styling)
                    var assetGeoJson = L.geoJSON(asset.geojson, {
                        style: function(feature) {
                            return { color: '#2d3436', weight: 3 };
                        },
                        pointToLayer: function(feature, latlng) {
                            var iconHtml = '<div style="background:#2d3436;color:white;width:24px;height:24px;border-radius:50%;text-align:center;line-height:24px;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);"><i class="' + getAssetIcon(asset.asset_type) + '" style="font-size:12px;"></i></div>';
                            var icon = L.divIcon({ html: iconHtml, className: '', iconSize: [24,24], iconAnchor: [12,12] });
                            return L.marker(latlng, {icon: icon});
                        }
                    });
                    
                    // Create progress geojson (styled by status)
                    var progressGeoJson = L.geoJSON(asset.geojson, {
                        style: function(feature) {
                            var weight = asset.status === 'completed' ? 6 : (asset.status === 'not_started' ? 3 : 5);
                            var dashArray = asset.status === 'not_started' ? '5, 5' : '';
                            return { color: color, weight: weight, dashArray: dashArray, opacity: 0.8 };
                        },
                        pointToLayer: function(feature, latlng) {
                            var iconHtml = '<div style="background:' + color + ';color:white;width:28px;height:28px;border-radius:50%;text-align:center;line-height:28px;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.4);"><i class="' + getAssetIcon(asset.asset_type) + '" style="font-size:14px;"></i></div>';
                            var icon = L.divIcon({ html: iconHtml, className: '', iconSize: [28,28], iconAnchor: [14,14] });
                            return L.marker(latlng, {icon: icon});
                        }
                    });

                    // Bind popups
                    var popupHtml = createAssetPopup(asset);
                    assetGeoJson.bindPopup(popupHtml, {maxWidth: 300});
                    progressGeoJson.bindPopup(popupHtml, {maxWidth: 300});

                    assetGeoJson.addTo(assetsLayer);
                    progressGeoJson.addTo(progressLayer);
                    
                    var b = assetGeoJson.getBounds();
                    if (b.isValid()) {
                        mapBounds.extend(b);
                        hasBounds = true;
                    }
                });
            }

            // 3. Render Media Markers
            if (data.media_markers && data.media_markers.length > 0) {
                data.media_markers.forEach(function(media) {
                    if (!media.lat || !media.lng) return;
                    
                    var iconHtml = '<div style="background:#e17055;color:white;width:28px;height:28px;border-radius:50%;text-align:center;line-height:28px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);"><i class="bi bi-camera-fill" style="font-size:13px;"></i></div>';
                    var icon = L.divIcon({ html: iconHtml, className: '', iconSize: [28,28], iconAnchor: [14,14] });
                    
                    var marker = L.marker([media.lat, media.lng], {icon: icon});
                    marker.bindPopup(createMediaPopup(media), {maxWidth: 280});
                    marker.addTo(mediaLayer);

                    mapBounds.extend([media.lat, media.lng]);
                    hasBounds = true;
                });
            }

            // Add all layers to map
            boundaryLayer.addTo(map);
            // By default show progress overlay instead of plain assets
            progressLayer.addTo(map);
            mediaLayer.addTo(map);

            // Add layer controls
            addLayerControls(map, {
                boundary: boundaryLayer,
                assets: assetsLayer,
                progress: progressLayer,
                media: mediaLayer
            });

            // Fit bounds
            if (hasBounds) {
                map.fitBounds(mapBounds.pad(0.1));
            }
        })
        .catch(function(err) {
            console.error("Error loading project GIS data:", err);
        });

    return {
        boundaryLayer: boundaryLayer,
        assetsLayer: assetsLayer,
        mediaLayer: mediaLayer,
        progressLayer: progressLayer
    };
}

/**
 * Add custom layer control panel
 */
function addLayerControls(map, layers) {
    var overlayMaps = {
        "Project Boundary": layers.boundary,
        "Asset Base Layer": layers.assets,
        "Construction Progress": layers.progress,
        "Geotagged Images": layers.media
    };
    
    L.control.layers(null, overlayMaps, { collapsed: false, position: 'topright' }).addTo(map);
}
