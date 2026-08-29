// Map Controller for Trajectory, Heatmaps, and Infrastructure Maps
class MapController {
    constructor() {
        this.trajMap = null;
        this.heatMap = null;
        this.infraMap = null;
        this.trajLayerGroup = null;
        this.heatLayer = null;
        this.infraLayerGroup = null;
        this.heatCameraMarkersGroup = null;
    }

    initMaps() {
        const defaultCenter = [28.6139, 77.2090]; // City center coordinates
        const defaultZoom = 12;

        const tileUrl = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
        const tileAttr = '&copy; <a href="https://carto.com/">CARTO</a> OpenStreetMap';

        // 1. Trajectory Map
        if (document.getElementById("trajectory-map") && !this.trajMap) {
            this.trajMap = L.map("trajectory-map").setView(defaultCenter, defaultZoom);
            L.tileLayer(tileUrl, { attribution: tileAttr, maxZoom: 19 }).addTo(this.trajMap);
            this.trajLayerGroup = L.layerGroup().addTo(this.trajMap);
        }

        // 2. Heatmap Map
        if (document.getElementById("heatmap-map") && !this.heatMap) {
            this.heatMap = L.map("heatmap-map").setView(defaultCenter, defaultZoom);
            L.tileLayer(tileUrl, { attribution: tileAttr, maxZoom: 19 }).addTo(this.heatMap);
            this.heatCameraMarkersGroup = L.layerGroup().addTo(this.heatMap);
        }

        // 3. Infrastructure Map
        if (document.getElementById("infra-map") && !this.infraMap) {
            this.infraMap = L.map("infra-map").setView(defaultCenter, defaultZoom);
            L.tileLayer(tileUrl, { attribution: tileAttr, maxZoom: 19 }).addTo(this.infraMap);
            this.infraLayerGroup = L.layerGroup().addTo(this.infraMap);
        }
    }

    invalidateSize() {
        setTimeout(() => {
            if (this.trajMap) this.trajMap.invalidateSize();
            if (this.heatMap) this.heatMap.invalidateSize();
            if (this.infraMap) this.infraMap.invalidateSize();
        }, 200);
    }

    renderTrajectory(waypoints, summary) {
        if (!this.trajMap || !this.trajLayerGroup) return;
        this.trajLayerGroup.clearLayers();

        if (!waypoints || waypoints.length === 0) return;

        const latLngs = [];

        waypoints.forEach((wp, idx) => {
            const pos = [wp.lat, wp.lng];
            latLngs.push(pos);

            let markerClass = "custom-waypoint-icon";
            if (wp.is_anomaly) markerClass += " anomaly";
            else if (idx === 0) markerClass += " start";
            else if (idx === waypoints.length - 1) markerClass += " end";

            const icon = L.divIcon({
                className: markerClass,
                html: `<span>${wp.step}</span>`,
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            });

            const marker = L.marker(pos, { icon }).addTo(this.trajLayerGroup);

            const anomalyTag = wp.is_anomaly
                ? `<div class="p-2 bg-red-950/80 border border-red-500 rounded text-red-300 text-xs mt-2 font-bold">⚠️ ${wp.anomaly_reason}</div>`
                : "";

            const popupContent = `
                <div style="min-width: 220px; font-family:'Inter', sans-serif;">
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155; padding-bottom:6px; margin-bottom:8px;">
                        <span style="font-weight:bold; font-size:12px; color:#38bdf8;">CHECKPOINT #${wp.step}</span>
                        <span style="font-size:10px; background:#1e293b; padding:2px 6px; border-radius:4px; color:#94a3b8;">${wp.camera_id}</span>
                    </div>
                    <div style="font-size:13px; font-weight:700; color:#f8fafc;">${wp.camera_name}</div>
                    <div style="font-size:11px; color:#94a3b8; margin-bottom:6px;">Sector: ${wp.sector}</div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px; font-size:11px; margin-top:6px; background:#0b0f19; padding:6px; border-radius:6px;">
                        <div><strong style="color:#64748b;">Time:</strong> ${wp.timestamp.split(' ')[1]}</div>
                        <div><strong style="color:#64748b;">Speed:</strong> ${wp.leg_speed_kmh} km/h</div>
                        <div><strong style="color:#64748b;">Distance:</strong> ${wp.leg_distance_km} km</div>
                        <div><strong style="color:#64748b;">OCR:</strong> ${Math.round(wp.ocr_conf*100)}%</div>
                    </div>
                    ${anomalyTag}
                </div>
            `;
            marker.bindPopup(popupContent);
        });

        // Draw animated polyline with direction glow
        const polyline = L.polyline(latLngs, {
            color: "#38bdf8",
            weight: 4,
            opacity: 0.85,
            dashArray: "8, 8",
            lineCap: "round"
        }).addTo(this.trajLayerGroup);

        this.trajMap.fitBounds(polyline.getBounds(), { padding: [40, 40] });
    }

    renderHeatmap(heatmapPoints, cameraNodes) {
        if (!this.heatMap) return;

        if (this.heatLayer) {
            this.heatMap.removeLayer(this.heatLayer);
        }
        if (this.heatCameraMarkersGroup) {
            this.heatCameraMarkersGroup.clearLayers();
        }

        if (window.L && L.heatLayer && heatmapPoints && heatmapPoints.length > 0) {
            this.heatLayer = L.heatLayer(heatmapPoints, {
                radius: 35,
                blur: 22,
                maxZoom: 15,
                max: 1.0,
                gradient: {
                    0.2: '#06b6d4',
                    0.4: '#10b981',
                    0.7: '#f59e0b',
                    1.0: '#ef4444'
                }
            }).addTo(this.heatMap);
        }

        // Add Camera node markers
        if (cameraNodes) {
            cameraNodes.forEach(cam => {
                const colorHex = cam.status_color === "red" ? "#ef4444" : cam.status_color === "amber" ? "#f59e0b" : "#10b981";
                const circle = L.circleMarker([cam.lat, cam.lng], {
                    radius: 8,
                    fillColor: colorHex,
                    color: "#ffffff",
                    weight: 2,
                    opacity: 0.9,
                    fillOpacity: 0.85
                }).addTo(this.heatCameraMarkersGroup);

                circle.bindPopup(`
                    <div style="font-family:'Inter', sans-serif;">
                        <strong style="color:#38bdf8;">${cam.name} (${cam.id})</strong><br>
                        <span style="font-size:11px; color:#94a3b8;">${cam.sector}</span>
                        <div style="margin-top:6px; font-size:12px;">
                            <div>Throughput: <strong>${cam.detection_count} vehicles</strong></div>
                            <div>Avg Speed: <strong>${cam.avg_speed} km/h</strong></div>
                            <div>Congestion: <span style="color:${colorHex}; font-weight:bold;">${cam.congestion_level}</span></div>
                        </div>
                    </div>
                `);
            });
        }
    }

    renderInfrastructure(cameras) {
        if (!this.infraMap || !this.infraLayerGroup) return;
        this.infraLayerGroup.clearLayers();

        if (!cameras) return;

        cameras.forEach(cam => {
            const isOnline = cam.status === "ONLINE";
            const iconHtml = `
                <div style="background:${isOnline ? '#0284c7' : '#64748b'}; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#fff; border:2px solid #fff; box-shadow:0 0 10px rgba(2,132,199,0.8);">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
                </div>
            `;

            const icon = L.divIcon({
                className: 'custom-cam-pin',
                html: iconHtml,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });

            const marker = L.marker([cam.lat, cam.lng], { icon }).addTo(this.infraLayerGroup);

            marker.bindPopup(`
                <div style="font-family:'Inter', sans-serif;">
                    <div style="font-weight:bold; color:#38bdf8;">${cam.name}</div>
                    <div style="font-size:11px; color:#94a3b8; margin-bottom:6px;">Node Code: ${cam.id} | ${cam.sector}</div>
                    <div style="font-size:11px;">
                        <div>Direction: <strong>${cam.direction}</strong></div>
                        <div>Type: <strong>${cam.camera_type}</strong></div>
                        <div>Status: <strong style="color:${isOnline ? '#10b981' : '#ef4444'};">${cam.status}</strong></div>
                        <div style="margin-top:4px; font-family:monospace; font-size:10px; color:#64748b;">${cam.lat.toFixed(4)} N, ${cam.lng.toFixed(4)} E</div>
                    </div>
                </div>
            `);
        });
    }
}

const mapController = new MapController();
