class MapController {
    constructor() {
        this.trajMap = null;
        this.heatMap = null;
        this.infraMap = null;
        this.predictiveMap = null;
        this.trajLayerGroup = null;
        this.heatLayer = null;
        this.infraLayerGroup = null;
        this.heatCameraMarkersGroup = null;
        this.predictiveLayerGroup = null;
        
        this.currentTheme = localStorage.getItem("free_map_theme") || "carto-dark";
        this.tileLayers = [];
    }

    getTileConfig(theme = this.currentTheme) {
        if (theme === "esri-dark") {
            return {
                url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                options: { attribution: '&copy; Esri &copy; OpenStreetMap', maxZoom: 18 }
            };
        } else if (theme === "osm-standard") {
            return {
                url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                options: { attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 }
            };
        } else if (theme === "carto-voyager") {
            return {
                url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
                options: { attribution: '&copy; CARTO &copy; OpenStreetMap', maxZoom: 19 }
            };
        }
        // Default CARTO Dark Matter (Free ICCC Dark Theme)
        return {
            url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            options: { attribution: '&copy; CARTO &copy; OpenStreetMap', maxZoom: 19 }
        };
    }

    setMapTheme(theme) {
        this.currentTheme = theme;
        localStorage.setItem("free_map_theme", theme);
        this.refreshTileLayers();
    }

    refreshTileLayers() {
        const config = this.getTileConfig();
        this.tileLayers.forEach(layerObj => {
            try {
                layerObj.map.removeLayer(layerObj.tile);
                const newTile = L.tileLayer(config.url, config.options).addTo(layerObj.map);
                layerObj.tile = newTile;
            } catch (e) {
                console.error("Error refreshing tile layer", e);
            }
        });
    }

    initMaps() {
        const nagpurCenter = [21.1458, 79.0882]; // Nagpur city center (Sitabuldi / Zero Mile)
        const defaultZoom = 13;

        const config = this.getTileConfig();
        this.tileLayers = [];

        // 1. Trajectory Map
        if (document.getElementById("trajectory-map") && !this.trajMap) {
            this.trajMap = L.map("trajectory-map").setView(nagpurCenter, defaultZoom);
            const tile = L.tileLayer(config.url, config.options).addTo(this.trajMap);
            this.tileLayers.push({ map: this.trajMap, tile: tile });
            this.trajLayerGroup = L.layerGroup().addTo(this.trajMap);
        }

        // 2. Predictive Handoff Engine Map
        if (document.getElementById("predictive-map") && !this.predictiveMap) {
            this.predictiveMap = L.map("predictive-map").setView(nagpurCenter, defaultZoom);
            const tile = L.tileLayer(config.url, config.options).addTo(this.predictiveMap);
            this.tileLayers.push({ map: this.predictiveMap, tile: tile });
            this.predictiveLayerGroup = L.layerGroup().addTo(this.predictiveMap);
        }

        // 3. Heatmap Map
        if (document.getElementById("heatmap-map") && !this.heatMap) {
            this.heatMap = L.map("heatmap-map").setView(nagpurCenter, defaultZoom);
            const tile = L.tileLayer(config.url, config.options).addTo(this.heatMap);
            this.tileLayers.push({ map: this.heatMap, tile: tile });
            this.heatCameraMarkersGroup = L.layerGroup().addTo(this.heatMap);
        }

        // 4. Infrastructure Map
        if (document.getElementById("infra-map") && !this.infraMap) {
            this.infraMap = L.map("infra-map").setView(nagpurCenter, defaultZoom);
            const tile = L.tileLayer(config.url, config.options).addTo(this.infraMap);
            this.tileLayers.push({ map: this.infraMap, tile: tile });
            this.infraLayerGroup = L.layerGroup().addTo(this.infraMap);
        }
    }

    invalidateSize() {
        setTimeout(() => {
            if (this.trajMap) this.trajMap.invalidateSize();
            if (this.predictiveMap) this.predictiveMap.invalidateSize();
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

    renderPredictiveHandoffMap(observedWaypoints, routeHypotheses, nextPredictions, offlineNodes) {
        if (!this.predictiveMap || !this.predictiveLayerGroup) return;
        this.predictiveLayerGroup.clearLayers();

        const allLatLngs = [];

        // 1. Render Confirmed OBSERVED Waypoints
        if (observedWaypoints && observedWaypoints.length > 0) {
            const observedCoords = [];
            observedWaypoints.forEach((wp, idx) => {
                const pos = [wp.lat, wp.lng];
                observedCoords.push(pos);
                allLatLngs.push(pos);

                let markerClass = "custom-waypoint-icon";
                if (idx === 0) markerClass += " start";
                else if (idx === observedWaypoints.length - 1) markerClass += " end";

                const icon = L.divIcon({
                    className: markerClass,
                    html: `<span>#${wp.step || (idx+1)}</span>`,
                    iconSize: [28, 28],
                    iconAnchor: [14, 14]
                });

                const marker = L.marker(pos, { icon }).addTo(this.predictiveLayerGroup);
                marker.bindPopup(`
                    <div style="min-width: 220px; font-family:'Inter', sans-serif;">
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155; padding-bottom:4px; margin-bottom:6px;">
                            <span style="font-weight:bold; font-size:11px; color:#10b981; text-transform:uppercase;">🟢 OBSERVED CHECKPOINT</span>
                            <span style="font-size:10px; background:#0f172a; padding:2px 6px; border-radius:4px; color:#38bdf8;">${wp.camera_id}</span>
                        </div>
                        <div style="font-size:12px; font-weight:700; color:#f8fafc;">${wp.camera_name || wp.name}</div>
                        <div style="font-size:11px; color:#94a3b8;">${wp.sector}</div>
                        <div style="margin-top:6px; font-size:11px; color:#cbd5e1;">
                            <div>Timestamp: <strong>${wp.timestamp ? wp.timestamp.split(' ')[1] : 'Recent'}</strong></div>
                            <div>Conf: <strong>${Math.round((wp.ocr_conf || 0.9)*100)}%</strong></div>
                        </div>
                    </div>
                `);
            });

            // Solid Cyan Polyline for Observed Route
            if (observedCoords.length > 1) {
                L.polyline(observedCoords, {
                    color: "#06b6d4",
                    weight: 4,
                    opacity: 0.9
                }).addTo(this.predictiveLayerGroup);
            }
        }

        // 2. Render INFERRED Route Hypotheses (Intermediate Unmonitored Junctions)
        if (routeHypotheses && routeHypotheses.length > 0) {
            routeHypotheses.forEach((hyp) => {
                const inferredCoords = [];
                hyp.steps.forEach((step) => {
                    if (step.lat && step.lng) {
                        const pos = [step.lat, step.lng];
                        inferredCoords.push(pos);
                        allLatLngs.push(pos);

                        if (step.status_type === "INFERRED") {
                            const icon = L.divIcon({
                                className: "custom-waypoint-icon inferred",
                                html: `<span style="color:#000;">⚡</span>`,
                                iconSize: [22, 22],
                                iconAnchor: [11, 11]
                            });

                            const m = L.marker(pos, { icon }).addTo(this.predictiveLayerGroup);
                            m.bindPopup(`
                                <div style="min-width: 200px; font-family:'Inter', sans-serif;">
                                    <div style="font-weight:bold; font-size:11px; color:#f59e0b; text-transform:uppercase; border-bottom:1px solid #334155; padding-bottom:4px; margin-bottom:6px;">
                                        🟡 INFERRED LOCATION (Unmonitored Junction)
                                    </div>
                                    <div style="font-size:12px; font-weight:700; color:#f8fafc;">${step.name}</div>
                                    <div style="font-size:11px; color:#94a3b8;">${step.sector} (${step.node_id})</div>
                                    <div style="margin-top:6px; font-size:11px; color:#f59e0b; background:#451a03; padding:4px 6px; border-radius:4px;">
                                        Hypothetical corridor connection
                                    </div>
                                </div>
                            `);
                        }
                    }
                });

                // Amber Dashed Polyline for Inferred Route Leg
                if (inferredCoords.length > 1) {
                    L.polyline(inferredCoords, {
                        color: "#f59e0b",
                        weight: 3,
                        dashArray: "6, 6",
                        opacity: 0.75
                    }).addTo(this.predictiveLayerGroup);
                }
            });
        }

        // 3. Render PREDICTED Downstream Target Cameras
        if (nextPredictions && nextPredictions.length > 0) {
            nextPredictions.forEach((pred) => {
                if (pred.lat && pred.lng) {
                    const pos = [pred.lat, pred.lng];
                    allLatLngs.push(pos);

                    const icon = L.divIcon({
                        className: "custom-waypoint-icon predicted",
                        html: `<span style="font-size:10px; font-weight:900;">${pred.percentage}%</span>`,
                        iconSize: [34, 34],
                        iconAnchor: [17, 17]
                    });

                    const m = L.marker(pos, { icon }).addTo(this.predictiveLayerGroup);

                    // Pulsing radius circle around predicted camera
                    L.circle(pos, {
                        radius: 250,
                        color: "#c084fc",
                        fillColor: "#a855f7",
                        fillOpacity: 0.15,
                        weight: 1.5,
                        dashArray: "4, 4"
                    }).addTo(this.predictiveLayerGroup);

                    m.bindPopup(`
                        <div style="min-width: 240px; font-family:'Inter', sans-serif;">
                            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155; padding-bottom:4px; margin-bottom:6px;">
                                <span style="font-weight:bold; font-size:11px; color:#c084fc; text-transform:uppercase;">🟣 PREDICTED NEXT CAMERA</span>
                                <span style="font-size:11px; background:#581c87; color:#f5d0fe; padding:2px 6px; border-radius:4px; font-weight:bold;">${pred.percentage}% PROB</span>
                            </div>
                            <div style="font-size:13px; font-weight:bold; color:#f8fafc;">${pred.camera_name}</div>
                            <div style="font-size:11px; color:#94a3b8;">${pred.sector} (${pred.camera_id})</div>
                            <div style="margin-top:8px; background:#0f172a; padding:8px; border-radius:6px; font-size:11px; border:1px solid #334155;">
                                <div><strong style="color:#c084fc;">Expected ETA:</strong> ${pred.eta_text}</div>
                                <div><strong style="color:#94a3b8;">Distance:</strong> ${pred.distance_km} km</div>
                                <div style="margin-top:4px; color:#e2e8f0; font-size:10px;">Handoff Watch Queue: <span style="color:#34d399; font-weight:bold;">ACTIVE</span></div>
                            </div>
                        </div>
                    `);
                }
            });
        }

        if (allLatLngs.length > 0) {
            this.predictiveMap.fitBounds(allLatLngs, { padding: [40, 40], maxZoom: 14 });
        }
    }

    renderInfrastructure(cameras) {
        if (!this.infraMap || !this.infraLayerGroup) return;
        this.infraLayerGroup.clearLayers();

        if (!cameras) return;

        cameras.forEach(cam => {
            const isOnline = cam.status === "ONLINE";
            const isDegraded = cam.status === "DEGRADED";
            const bgColor = isOnline ? '#0284c7' : isDegraded ? '#d97706' : '#ef4444';
            const iconHtml = `
                <div style="background:${bgColor}; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#fff; border:2px solid #fff; box-shadow:0 0 10px ${bgColor};">
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
                        <div>Status: <strong style="color:${isOnline ? '#10b981' : isDegraded ? '#f59e0b' : '#ef4444'};">${cam.status}</strong></div>
                        <div style="margin-top:4px; font-family:monospace; font-size:10px; color:#64748b;">${cam.lat.toFixed(4)} N, ${cam.lng.toFixed(4)} E</div>
                    </div>
                </div>
            `);
        });
    }
}

const mapController = new MapController();
