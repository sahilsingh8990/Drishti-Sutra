// Main Frontend Application Controller
class App {
    constructor() {
        this.currentTab = 'live';
        this.ws = null;
        this.cameras = [];
        this.liveFeedActive = false;
        this.renderedDetectionIds = new Set();
    }

    async init() {
        this.initTheme();
        this.startClock();
        mapController.initMaps();
        this.setupTabNavigation();
        this.connectWebSocket();

        await this.loadCameras();
        await this.loadKPIs();
        await this.loadRecentDetections();
        await this.loadRecentAlerts();
        await this.loadModelStatus();
        await this.loadAnalyticsTab();
        this.setupEventListeners();
        this.searchTrajectory("MH49AE2355");
        this.searchPredictiveHandoff("25BH2534O");
        this.loadActiveWatchQueue();
        this.startDetectionsPolling();
    }

    initTheme() {
        if (window.themeController) {
            themeController.initTheme();
        }
    }

    applyTheme(theme, notify = true) {
        if (window.themeController) {
            themeController.setTheme(theme, notify);
        }
    }

    toggleTheme() {
        if (window.themeController) {
            themeController.toggleTheme();
        }
    }

    startClock() {
        const clockEl = document.getElementById("system-clock");
        const update = () => {
            const now = new Date();
            if (clockEl) {
                clockEl.textContent = now.toLocaleTimeString('en-US', { hour12: false }) + " UTC+5:30";
            }
        };
        update();
        setInterval(update, 1000);
    }

    setupTabNavigation() {
        const tabBtns = document.querySelectorAll(".tab-btn");
        tabBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                const target = btn.dataset.tab;
                this.switchTab(target);
            });
        });
    }

    switchTab(tabName) {
        this.currentTab = tabName;

        document.querySelectorAll(".tab-btn").forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.className = "tab-btn w-full px-3 py-2 rounded text-xs font-bold transition-all flex items-center space-x-2.5 bg-sky-950/80 text-sky-300 border border-sky-700/60 shadow-sm";
            } else {
                btn.className = "tab-btn w-full px-3 py-2 rounded text-xs font-semibold transition-all flex items-center space-x-2.5 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200";
            }
        });

        document.querySelectorAll(".tab-content").forEach(section => {
            if (section.id === `tab-${tabName}`) {
                section.classList.remove("hidden");
            } else {
                section.classList.add("hidden");
            }
        });

        mapController.invalidateSize();

        if (tabName === "predictive") {
            this.loadPredictiveTab();
        } else if (tabName === "analytics") {
            this.loadAnalyticsTab();
            setTimeout(() => {
                mapController.invalidateSize();
                analyticsCharts.resizeCharts();
            }, 150);
        } else if (tabName === "security") {
            this.loadBlacklist();
            this.loadRecentAlerts();
        } else if (tabName === "infrastructure") {
            mapController.renderInfrastructure(this.cameras);
            this.renderInfrastructureTable();
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/live`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log("Connected to Live Command Center WebSocket");
            const statusEl = document.getElementById("connection-status");
            if (statusEl) {
                statusEl.innerHTML = `
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span class="text-[11px] text-emerald-400 font-semibold uppercase tracking-wider">Surveillance Grid Online</span>
                `;
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.event === "NEW_DETECTION") {
                    this.handleNewDetection(msg.data);
                } else if (msg.event === "SECURITY_ALERT") {
                    this.handleSecurityAlert(msg.data);
                } else if (msg.event === "HANDOFF_CREATED") {
                    this.handleHandoffCreated(msg.data);
                } else if (msg.event === "HANDOFF_REACQUIRED") {
                    this.handleHandoffReacquired(msg.data);
                } else if (msg.event === "CAMERA_HEALTH_CHANGED") {
                    this.handleCameraHealthChanged(msg.data);
                }
            } catch (e) {
                console.error("WS Parse error", e);
            }
        };

        this.ws.onclose = () => {
            const statusEl = document.getElementById("connection-status");
            if (statusEl) {
                statusEl.innerHTML = `
                    <span class="w-2 h-2 rounded-full bg-amber-400"></span>
                    <span class="text-[11px] text-amber-400 font-semibold uppercase tracking-wider">Reconnecting Feed...</span>
                `;
            }
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    async loadRecentDetections() {
        try {
            const res = await fetch("/api/detections?limit=25");
            const data = await res.json();
            if (Array.isArray(data)) {
                // Filter for live webcam or inspector detections
                const liveDetections = data.filter(d => {
                    const vt = (d.vehicle_type || "").toLowerCase();
                    return vt.includes("live") || vt.includes("webcam") || vt.includes("stream") || vt.includes("manual") || vt.includes("inspector");
                });

                const reversed = [...liveDetections].reverse();
                reversed.forEach(det => {
                    if (det.id && !this.renderedDetectionIds.has(det.id)) {
                        this.handleNewDetection(det, false);
                    }
                });
            }
        } catch (e) {
            console.error("Failed to load recent detections", e);
        }
    }

    startDetectionsPolling() {
        setInterval(() => {
            this.loadRecentDetections();
            this.loadKPIs();
        }, 2500);
    }

    handleNewDetection(detection, playSound = true) {
        const plateKey = (detection.plate_number || "").replace(/[^A-Z0-9]/g, "");
        const ticker = document.getElementById("live-detection-ticker");

        if (ticker && plateKey) {
            let existingCard = document.getElementById(`ticker-card-${plateKey}`);
            const timeStr = detection.timestamp ? (detection.timestamp.includes(' ') ? detection.timestamp.split(' ')[1] : detection.timestamp) : 'Recent';

            if (existingCard) {
                const timeEl = existingCard.querySelector(".card-time-val");
                if (timeEl) timeEl.textContent = timeStr;
                return;
            }

            if (detection.id) {
                this.renderedDetectionIds.add(detection.id);
            }

            const card = document.createElement("div");
            card.id = `ticker-card-${plateKey}`;
            card.className = "op-card flex items-center justify-between transition-all";
            
            const isBlacklisted = detection.is_blacklisted;
            const plateBg = isBlacklisted ? "bg-red-950 text-red-300 border-red-800" : "bg-sky-950 text-sky-300 border-sky-800";
            const camName = detection.camera_name || `Camera ${detection.camera_id || 'CAM-01'}`;

            card.innerHTML = `
                <div class="flex items-center space-x-2.5">
                    <div class="w-8 h-8 rounded bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-300 font-mono text-xs font-bold">
                        ${(detection.camera_id || 'CAM-01').replace('CAM-', '#')}
                    </div>
                    <div>
                        <div class="flex items-center space-x-1.5">
                            <span class="font-mono font-bold text-xs tracking-wider px-1.5 py-0.2 rounded border ${plateBg}">${detection.plate_number}</span>
                            ${isBlacklisted ? '<span class="op-badge op-badge-offline">FLAGGED</span>' : ''}
                        </div>
                        <div class="text-[10px] text-slate-400 mt-0.5">${camName}</div>
                    </div>
                </div>
                <div class="text-right text-xs font-mono">
                    <div class="font-bold text-slate-200">${detection.speed_kmh || 45} km/h</div>
                    <div class="card-time-val text-[10px] text-slate-500 mt-0.5">${timeStr}</div>
                </div>
            `;

            ticker.insertBefore(card, ticker.firstChild);
            if (ticker.children.length > 25) {
                ticker.lastChild.remove();
            }
        }

        const totalEl = document.getElementById("kpi-total-detections");
        if (totalEl) {
            const curr = parseInt(totalEl.textContent.replace(/,/g, '')) || 0;
            totalEl.textContent = (curr + 1).toLocaleString();
        }

        // Notify ONLY if vehicle is blacklisted / flagged
        if (detection.is_blacklisted) {
            alertsManager.showToast(
                "CRITICAL WATCHLIST INTERCEPTION",
                `Blacklisted vehicle ${detection.plate_number} detected at ${detection.camera_name || detection.camera_id}`,
                "CRITICAL",
                6000
            );
            alertsManager.playAlertTone("critical");
        }
    }

    handleSecurityAlert(alert) {
        alertsManager.showToast(
            alert.alert_type === "CLONED_PLATE" ? "CLONED PLATE ANOMALY" : "SECURITY TARGET DETECTED",
            alert.description,
            alert.severity || "CRITICAL"
        );

        const alertsKpi = document.getElementById("kpi-active-alerts");
        if (alertsKpi) {
            const curr = parseInt(alertsKpi.textContent) || 0;
            alertsKpi.textContent = curr + 1;
        }

        const banner = document.getElementById("urgent-alert-banner");
        if (banner) {
            banner.classList.remove("hidden");
            document.getElementById("urgent-alert-text").textContent = alert.description;
        }
    }

    handleHandoffCreated(data) {
        if (data.is_blacklisted || data.priority === "CRITICAL") {
            alertsManager.showToast(
                "Priority Blacklist Handoff Dispatched",
                `Watching for target ${data.vehicle_plate} downstream from ${data.source_camera}`,
                "HIGH",
                4000
            );
        }
        if (this.currentTab === "predictive") {
            this.loadActiveWatchQueue();
        }
    }

    handleHandoffReacquired(evalData) {
        if (evalData.is_blacklisted || evalData.priority === "CRITICAL") {
            const title = evalData.was_correct ? "Watchlist Target Reacquired" : "Watchlist Vehicle Diverted Path";
            const msg = `${evalData.vehicle_plate} detected at ${evalData.actual_camera} (Predicted: ${evalData.predicted_camera}).`;
            alertsManager.showToast(title, msg, "CRITICAL", 5000);
        }

        if (this.currentTab === "predictive") {
            this.loadPredictiveTab();
        }
    }

    handleCameraHealthChanged(data) {
        alertsManager.showToast(
            "Camera Grid Health Updated",
            `${data.camera_id} set to ${data.status}. Observability: ${data.observability.observability_percentage}%`,
            data.status === "ONLINE" ? "INFO" : "HIGH"
        );
        if (this.currentTab === "predictive") {
            this.loadPredictiveTab();
        }
    }

    async loadPredictiveTab() {
        await Promise.all([
            this.loadActiveWatchQueue(),
            this.loadNetworkObservability(),
            this.loadReacquisitionStats(),
            this.loadCameraHealthToggles()
        ]);

        const currSearch = document.getElementById("predictive-search-input")?.value || "25BH2534O";
        this.searchPredictiveHandoff(currSearch);
    }

    async searchPredictiveHandoff(plateNumber) {
        if (!plateNumber) {
            plateNumber = document.getElementById("predictive-search-input")?.value || "25BH2534O";
        }
        plateNumber = plateNumber.trim().toUpperCase();
        const input = document.getElementById("predictive-search-input");
        if (input) input.value = plateNumber;

        try {
            const res = await fetch(`/api/predictive/track/${encodeURIComponent(plateNumber)}`);
            const data = await res.json();

            // 1. Identity Header
            const resolvedEl = document.getElementById("pred-resolved-plate");
            if (resolvedEl) resolvedEl.textContent = data.plate_number;

            const rawEl = document.getElementById("pred-raw-ocr");
            if (rawEl) rawEl.textContent = data.raw_ocr;

            const normEl = document.getElementById("pred-norm-ocr");
            if (normEl) normEl.textContent = data.normalized_ocr;

            const confPct = Math.round(data.identity_confidence * 100);
            const confValEl = document.getElementById("pred-conf-val");
            if (confValEl) confValEl.textContent = `${confPct}%`;

            const confBarEl = document.getElementById("pred-conf-bar");
            if (confBarEl) confBarEl.style.width = `${confPct}%`;

            const lastNodeEl = document.getElementById("pred-last-node");
            if (lastNodeEl) {
                const lastWp = data.observed_waypoints && data.observed_waypoints.length > 0 ? data.observed_waypoints[data.observed_waypoints.length - 1] : null;
                lastNodeEl.textContent = lastWp ? `${lastWp.camera_name} (${lastWp.camera_id})` : "CAM-01 (Connaught Place)";
            }

            const sightingsEl = document.getElementById("pred-sightings-count");
            if (sightingsEl) {
                sightingsEl.textContent = `${data.observed_waypoints?.length || 1} Checkpoint(s)`;
            }

            const blBadge = document.getElementById("pred-blacklist-badge");
            if (blBadge) {
                if (data.is_blacklisted) {
                    blBadge.classList.remove("hidden");
                } else {
                    blBadge.classList.add("hidden");
                }
            }

            // 2. Candidate Identities Breakdown
            this.renderCandidateIdentities(data.candidate_identities, data.plate_number);

            // 3. Spatio-Temporal GIS Tri-State Map
            mapController.renderPredictiveHandoffMap(
                data.observed_waypoints,
                data.route_hypotheses,
                data.next_camera_predictions
            );

            // 4. Explainability Breakdown
            const firstPred = data.next_camera_predictions && data.next_camera_predictions.length > 0 ? data.next_camera_predictions[0] : null;
            this.renderExplainabilityFactors(firstPred?.explainability_factors || []);

            // 5. Ranked Next Cameras
            this.renderRankedNextCameras(data.next_camera_predictions || []);

        } catch (e) {
            console.error("Predictive track search error", e);
        }
    }

    renderCandidateIdentities(candidates, resolvedPlate) {
        const container = document.getElementById("pred-candidates-list");
        if (!container || !candidates) return;

        container.innerHTML = "";
        candidates.forEach(cand => {
            const isSelected = cand.plate === resolvedPlate;
            const card = document.createElement("div");
            card.className = `p-3 rounded-xl border transition-all ${
                isSelected
                    ? "bg-purple-950/40 border-purple-500/80 shadow-lg shadow-purple-950/50"
                    : "bg-slate-900/80 border-slate-800 hover:border-slate-700"
            }`;

            card.innerHTML = `
                <div class="flex items-center justify-between mb-1.5">
                    <span class="font-mono font-extrabold text-sm ${isSelected ? 'text-purple-300' : 'text-slate-200'}">${cand.plate}</span>
                    <span class="text-xs font-mono font-bold ${cand.probability >= 0.7 ? 'text-emerald-400' : cand.probability >= 0.2 ? 'text-amber-400' : 'text-slate-400'}">${cand.percentage}%</span>
                </div>
                <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mb-2">
                    <div class="h-full rounded-full ${isSelected ? 'bg-gradient-to-r from-purple-500 to-emerald-400' : 'bg-slate-600'}" style="width: ${cand.percentage}%"></div>
                </div>
                <div class="text-[10px] text-slate-400 flex items-center justify-between">
                    <span>${cand.is_valid_structure ? '✓ Valid Indian' : cand.plate === 'Other' ? 'Residual Error' : 'OCR Permutation'}</span>
                    ${isSelected ? '<span class="text-purple-400 font-bold">PRIMARY</span>' : ''}
                </div>
            `;
            container.appendChild(card);
        });
    }

    renderExplainabilityFactors(factors) {
        const container = document.getElementById("pred-explainability-grid");
        if (!container) return;

        if (!factors || factors.length === 0) {
            container.innerHTML = `<div class="text-xs text-slate-500 col-span-2 py-3 text-center">No prediction factors available.</div>`;
            return;
        }

        container.innerHTML = "";
        factors.forEach(f => {
            const card = document.createElement("div");
            card.className = "factor-chip flex items-start space-x-3";
            card.innerHTML = `
                <div class="p-2 rounded-lg bg-purple-500/20 text-purple-300 flex-shrink-0">
                    <i data-lucide="check-circle" class="w-4 h-4"></i>
                </div>
                <div class="min-w-0 flex-1">
                    <div class="flex items-center justify-between">
                        <span class="font-bold text-xs text-slate-200">${f.factor_name}</span>
                        <span class="text-[11px] font-mono font-bold text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/40">${f.score}</span>
                    </div>
                    <p class="text-[11px] text-slate-400 mt-1 leading-relaxed">${f.description}</p>
                </div>
            `;
            container.appendChild(card);
        });
        if (window.lucide) lucide.createIcons();
    }

    renderRankedNextCameras(predictions) {
        const container = document.getElementById("pred-ranked-cameras-list");
        if (!container) return;

        if (!predictions || predictions.length === 0) {
            container.innerHTML = `<div class="text-xs text-slate-500 py-6 text-center">No downstream cameras predicted.</div>`;
            return;
        }

        container.innerHTML = "";
        predictions.forEach((p, idx) => {
            const card = document.createElement("div");
            card.className = "p-3 bg-slate-900/90 rounded-xl border border-slate-800 hover:border-purple-500/50 transition-all flex items-center justify-between";
            card.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 rounded-lg bg-purple-950 border border-purple-800 flex items-center justify-center font-mono font-bold text-purple-300 text-xs">
                        #${idx + 1}
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-bold text-xs text-slate-200">${p.camera_name}</span>
                            <span class="text-[10px] font-mono text-purple-400 bg-purple-950 px-1.5 py-0.2 rounded border border-purple-800">${p.camera_id}</span>
                        </div>
                        <div class="text-[11px] text-slate-400 mt-0.5">${p.sector} &bull; ${p.distance_km} km</div>
                    </div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-black font-mono text-purple-300">${p.percentage}%</div>
                    <div class="text-[10px] font-mono text-emerald-400 mt-0.5">ETA: ${p.eta_text}</div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    async loadActiveWatchQueue() {
        try {
            const res = await fetch("/api/predictive/handoffs");
            const handoffs = await res.json();
            this.renderActiveWatchQueue(handoffs);
        } catch (e) {
            console.error("Failed to load active watch queue", e);
        }
    }

    renderActiveWatchQueue(handoffs) {
        const container = document.getElementById("pred-active-watch-list");
        if (!container) return;

        if (!handoffs || handoffs.length === 0) {
            container.innerHTML = `<div class="text-xs text-slate-500 py-8 text-center">No active camera watch requests.</div>`;
            return;
        }

        container.innerHTML = "";
        const watchingCams = new Set();

        handoffs.forEach(h => {
            if (h.status === "WATCHING") {
                watchingCams.add(h.target_camera_id);
            }
            const card = document.createElement("div");
            card.className = "p-3 bg-purple-950/20 rounded-xl border border-purple-500/40 flex items-center justify-between";
            card.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="w-2.5 h-2.5 rounded-full bg-purple-400 animate-ping"></div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-mono font-black text-xs text-purple-300">${h.vehicle_plate}</span>
                            <span class="text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${h.priority === 'CRITICAL' ? 'bg-red-600 text-white animate-pulse' : 'bg-purple-900 text-purple-200'}">${h.priority}</span>
                        </div>
                        <div class="text-[11px] text-slate-300 mt-1 font-semibold">Node: ${h.target_camera_id} (${h.target_camera_name})</div>
                    </div>
                </div>
                <div class="text-right">
                    <span class="text-[10px] font-bold text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">${h.eta_text}</span>
                    <div class="text-[10px] text-slate-500 mt-1">${h.percentage}% Prob</div>
                </div>
            `;
            container.appendChild(card);
        });

        // Update Live Matrix Camera Cards
        ['CAM-01', 'CAM-02', 'CAM-07', 'CAM-10'].forEach(cid => {
            const card = document.getElementById(`live-card-${cid}`);
            const badge = document.getElementById(`watch-badge-${cid}`);
            if (watchingCams.has(cid)) {
                if (card) card.classList.add("watching-glow");
                if (badge) badge.classList.remove("hidden");
            } else {
                if (card) card.classList.remove("watching-glow");
                if (badge) badge.classList.add("hidden");
            }
        });
    }

    async loadNetworkObservability() {
        try {
            const res = await fetch("/api/predictive/network-observability");
            const obs = await res.json();

            const pctEl = document.getElementById("pred-observability-pct");
            if (pctEl) {
                pctEl.textContent = `${obs.observability_percentage}%`;
                pctEl.className = `text-2xl font-black font-mono ${
                    obs.observability_percentage >= 90 ? 'text-emerald-400' : obs.observability_percentage >= 70 ? 'text-amber-400' : 'text-red-400'
                }`;
            }

            const blindSpotContainer = document.getElementById("blind-spots-alert-container");
            if (blindSpotContainer) {
                if (obs.blind_spots && obs.blind_spots.length > 0) {
                    blindSpotContainer.innerHTML = obs.blind_spots.map(b => `
                        <div class="p-2.5 rounded-lg bg-red-950/40 border border-red-500/50 text-red-200 text-xs flex items-center justify-between">
                            <div class="flex items-center space-x-2">
                                <i data-lucide="alert-circle" class="w-4 h-4 text-red-400 flex-shrink-0"></i>
                                <span><strong>${b.camera_id} (${b.status}):</strong> ${b.impact}</span>
                            </div>
                        </div>
                    `).join("");
                } else {
                    blindSpotContainer.innerHTML = `
                        <div class="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-500/40 text-emerald-300 text-xs flex items-center space-x-2">
                            <i data-lucide="shield-check" class="w-4 h-4 text-emerald-400"></i>
                            <span>All primary surveillance corridors have full topological coverage (0 blind spots).</span>
                        </div>
                    `;
                }
                if (window.lucide) lucide.createIcons();
            }
        } catch (e) {
            console.error("Failed to load network observability", e);
        }
    }

    async loadCameraHealthToggles() {
        try {
            const res = await fetch("/api/cameras/health");
            const data = await res.json();
            const container = document.getElementById("camera-health-toggles-grid");
            if (!container) return;

            container.innerHTML = "";
            data.cameras.forEach(c => {
                const status = c.graph_status || c.status;
                const isOnline = status === "ONLINE";
                const isDegraded = status === "DEGRADED";

                const btn = document.createElement("button");
                btn.className = `p-2 rounded-lg border text-[11px] font-mono font-bold flex flex-col items-center justify-center transition-all ${
                    isOnline
                        ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-300 hover:bg-emerald-900/60"
                        : isDegraded
                        ? "bg-amber-950/40 border-amber-500/50 text-amber-300 hover:bg-amber-900/60"
                        : "bg-red-950/40 border-red-500/50 text-red-300 hover:bg-red-900/60"
                }`;

                btn.innerHTML = `
                    <span>${c.id}</span>
                    <span class="text-[9px] uppercase mt-0.5 ${isOnline ? 'text-emerald-400' : isDegraded ? 'text-amber-400' : 'text-red-400'}">${status}</span>
                `;

                btn.onclick = () => this.toggleCameraHealth(c.id, status);
                container.appendChild(btn);
            });
        } catch (e) {
            console.error("Failed to load camera health toggles", e);
        }
    }

    async loadAnalyticsTab() {
        try {
            // 1. Fetch Hourly Volume Trends, Speed Distribution & Camera Density
            const resTrends = await fetch("/api/analytics/hourly-trends");
            const trendsData = await resTrends.json();

            analyticsCharts.renderHourlyVolume(trendsData.hours || [], trendsData.volumes || []);
            analyticsCharts.renderSpeedDistribution(trendsData.speed_distribution || {});
            analyticsCharts.renderCameraTraffic(trendsData.camera_density || []);

            // 2. Fetch GIS Heatmap & Camera Node Markers
            const resHeatmap = await fetch("/api/analytics/heatmap");
            const heatData = await resHeatmap.json();
            mapController.renderHeatmap(heatData.heatmap_points || [], heatData.camera_nodes || []);

            setTimeout(() => {
                mapController.invalidateSize();
                analyticsCharts.resizeCharts();
            }, 100);

        } catch (e) {
            console.error("Failed to load analytics tab data", e);
        }
    }

    async toggleCameraHealth(camId, currentStatus) {
        const nextStatus = currentStatus === "ONLINE" ? "OFFLINE" : currentStatus === "OFFLINE" ? "DEGRADED" : "ONLINE";
        try {
            await fetch(`/api/cameras/${camId}/status`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: nextStatus })
            });
            await this.loadNetworkObservability();
            await this.loadCameraHealthToggles();
            const currSearch = document.getElementById("predictive-search-input")?.value || "25BH2534O";
            this.searchPredictiveHandoff(currSearch);
        } catch (e) {
            console.error("Toggle camera health error", e);
        }
    }

    async loadReacquisitionStats() {
        try {
            const res = await fetch("/api/predictive/reacquisition-stats");
            const stats = await res.json();

            const accEl = document.getElementById("pred-accuracy-metric");
            if (accEl) {
                accEl.textContent = `${stats.accuracy_percentage}%`;
            }

            this.renderReacquisitionLogs(stats.recent_evaluations || []);
        } catch (e) {
            console.error("Failed to load reacquisition stats", e);
        }
    }

    renderReacquisitionLogs(logs) {
        const container = document.getElementById("reacquisition-logs-list");
        if (!container) return;

        if (!logs || logs.length === 0) {
            container.innerHTML = `<div class="text-xs text-slate-500 py-6 text-center">No reacquisition logs yet.</div>`;
            return;
        }

        container.innerHTML = "";
        logs.forEach(l => {
            const card = document.createElement("div");
            card.className = `p-3 rounded-xl border flex items-center justify-between text-xs ${
                l.was_correct
                    ? "bg-emerald-950/20 border-emerald-500/40"
                    : "bg-amber-950/20 border-amber-500/40"
            }`;

            card.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="p-1.5 rounded-lg ${l.was_correct ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}">
                        <i data-lucide="${l.was_correct ? 'check' : 'alert-circle'}" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-mono font-bold text-slate-200">${l.vehicle_plate}</span>
                            <span class="text-[10px] font-mono px-1.5 py-0.2 rounded font-bold uppercase ${
                                l.was_correct ? 'bg-emerald-900 text-emerald-200' : 'bg-amber-900 text-amber-200'
                            }">${l.was_correct ? 'CORRECT REACQUISITION' : 'PATH DIVERGENCE'}</span>
                        </div>
                        <div class="text-[11px] text-slate-400 mt-0.5">
                            Target: <strong>${l.predicted_camera}</strong> &bull; Actual: <strong>${l.actual_camera}</strong>
                        </div>
                    </div>
                </div>
                <div class="text-right font-mono">
                    <div class="font-bold ${l.was_correct ? 'text-emerald-400' : 'text-amber-400'}">${Math.round(l.prediction_confidence * 100)}% Conf</div>
                    <div class="text-[10px] text-slate-500 mt-0.5">ETA Diff: ${l.eta_error_sec > 0 ? '+' : ''}${l.eta_error_sec}s</div>
                </div>
            `;
            container.appendChild(card);
        });
        if (window.lucide) lucide.createIcons();
    }

    async loadModelStatus() {
        try {
            const res = await fetch("/api/model/status");
            const data = await res.json();
            const modelInfoEl = document.getElementById("model-status-info");
            if (modelInfoEl) {
                modelInfoEl.innerHTML = `
                    <div class="flex items-center space-x-2">
                        <span class="w-2 h-2 rounded-full ${data.model_loaded ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}"></span>
                        <span class="font-mono font-bold text-xs text-slate-200">${data.model_file}</span>
                        <span class="text-[10px] bg-cyan-950 text-cyan-400 px-2 py-0.5 rounded border border-cyan-800">${data.model_size_mb} MB</span>
                    </div>
                    <div class="text-[11px] text-slate-400 mt-1">${data.architecture} &bull; ${data.ocr_engine}</div>
                `;
            }
        } catch (e) {
            console.error("Failed to load model status", e);
        }
    }

    toggleLiveWebcamStream() {
        const feedImg = document.getElementById("live-webcam-feed-img");
        const placeholder = document.getElementById("live-webcam-placeholder");
        const btn = document.getElementById("btn-toggle-webcam");

        this.liveFeedActive = !this.liveFeedActive;

        if (this.liveFeedActive) {
            // Clear ticker list to display strictly real live webcam detections
            const ticker = document.getElementById("live-detection-ticker");
            if (ticker) ticker.innerHTML = "";

            feedImg.src = "/api/video-feed";
            feedImg.classList.remove("hidden");
            placeholder.classList.add("hidden");
            btn.innerHTML = `<i data-lucide="video-off" class="w-4 h-4 text-red-400"></i><span>Stop Live YOLO Feed</span>`;
            alertsManager.showToast("Live ANPR Stream Active", "Processing camera feed with plate_model.pt + EasyOCR", "INFO");
        } else {
            feedImg.src = "";
            feedImg.classList.add("hidden");
            placeholder.classList.remove("hidden");
            btn.innerHTML = `<i data-lucide="video" class="w-4 h-4 text-cyan-400"></i><span>Start Live Webcam ANPR</span>`;
        }
        if (window.lucide) lucide.createIcons();
    }

    async inspectUploadedImage(file) {
        if (!file) return;

        const resultContainer = document.getElementById("inspector-results");
        const resultImg = document.getElementById("inspector-annotated-img");
        const platesList = document.getElementById("inspector-detected-plates");

        const formData = new FormData();
        formData.append("file", file);

        alertsManager.showToast("Running ANPR Model", "Running plate_model.pt and OCR on uploaded file...", "INFO");

        try {
            const res = await fetch("/api/anpr/inspect-image", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (!data.success) {
                alert("Image processing failed: " + (data.error || "Unknown error"));
                return;
            }

            resultContainer.classList.remove("hidden");
            resultImg.src = data.annotated_image;

            platesList.innerHTML = "";
            if (data.plates_detected.length === 0) {
                platesList.innerHTML = `<div class="text-xs text-amber-400 p-2 bg-amber-950/40 rounded border border-amber-800">No license plate localized in this image.</div>`;
            } else {
                data.plates_detected.forEach(p => {
                    const card = document.createElement("div");
                    card.className = "p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between";
                    card.innerHTML = `
                        <div>
                            <div class="text-xs text-slate-400 uppercase font-bold">Detected Plate</div>
                            <div class="text-lg font-black font-mono text-cyan-300 tracking-wider">${p.plate_number}</div>
                            <div class="text-[11px] text-slate-400 mt-0.5">YOLO Conf: <strong>${Math.round(p.detection_conf*100)}%</strong> &bull; OCR Conf: <strong>${Math.round(p.ocr_conf*100)}%</strong></div>
                        </div>
                        <button class="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs" onclick="app.searchTrajectory('${p.plate_number}'); app.switchTab('trajectory')">
                            Track Trajectory →
                        </button>
                    `;
                    platesList.appendChild(card);
                });
            }

            alertsManager.showToast("Inspection Complete", `Detected ${data.count} plate(s) with plate_model.pt!`, "INFO");
        } catch (e) {
            console.error("Inspect image error", e);
            alert("Error running ANPR on image: " + e);
        }
    }

    async loadCameras() {
        try {
            const res = await fetch("/api/cameras");
            this.cameras = await res.json();
            const onlineCount = this.cameras.filter(c => c.status === "ONLINE").length;
            const camKpi = document.getElementById("kpi-active-cameras");
            if (camKpi) camKpi.textContent = `${onlineCount} / ${this.cameras.length}`;
        } catch (e) {
            console.error("Failed to load cameras", e);
        }
    }

    async loadKPIs() {
        try {
            const res = await fetch("/api/analytics/overview");
            const kpis = await res.json();

            document.getElementById("kpi-total-detections").textContent = kpis.total_detections.toLocaleString();
            document.getElementById("kpi-unique-vehicles").textContent = kpis.unique_vehicles.toLocaleString();
            document.getElementById("kpi-active-alerts").textContent = kpis.active_alerts;
            document.getElementById("kpi-congestion-index").textContent = `${kpis.congestion_index}%`;
        } catch (e) {
            console.error("Failed to load KPIs", e);
        }
    }

    async loadRecentDetections() {
        try {
            const res = await fetch("/api/detections?limit=15");
            const detections = await res.json();
            const ticker = document.getElementById("live-detection-ticker");
            if (!ticker) return;

            ticker.innerHTML = "";
            detections.forEach(det => {
                const card = document.createElement("div");
                card.className = "p-3 bg-slate-900/80 rounded-xl border border-slate-800 hover:border-cyan-500/50 transition-all flex items-center justify-between";
                card.innerHTML = `
                    <div class="flex items-center space-x-3">
                        <div class="w-9 h-9 rounded-lg bg-slate-800/80 flex items-center justify-center text-slate-300 font-mono text-xs">
                            ${det.camera_id.replace('CAM-', '#')}
                        </div>
                        <div>
                            <div class="flex items-center space-x-2">
                                <span class="font-mono font-extrabold text-sm tracking-wide px-2 py-0.5 rounded border bg-cyan-500/10 text-cyan-300 border-cyan-500/30">${det.plate_number}</span>
                            </div>
                            <div class="text-[11px] text-slate-400 mt-1">${det.camera_name} &bull; <span class="text-slate-500">${det.sector}</span></div>
                        </div>
                    </div>
                    <div class="text-right text-xs">
                        <div class="font-mono font-bold text-slate-300">${det.speed_kmh} km/h</div>
                        <div class="text-[10px] text-slate-500 mt-0.5">${det.timestamp.split(' ')[1]}</div>
                    </div>
                `;
                ticker.appendChild(card);
            });
        } catch (e) {
            console.error("Failed to load recent detections", e);
        }
    }

    async searchTrajectory(plateNumber) {
        if (!plateNumber) {
            plateNumber = document.getElementById("traj-search-input").value;
        }
        if (!plateNumber) return;

        plateNumber = plateNumber.trim().toUpperCase();
        document.getElementById("traj-search-input").value = plateNumber;

        try {
            const res = await fetch(`/api/trajectory/${encodeURIComponent(plateNumber)}`);
            const data = await res.json();

            const notFoundEl = document.getElementById("traj-not-found");
            const contentEl = document.getElementById("traj-results-container");

            if (!data.found) {
                notFoundEl.classList.remove("hidden");
                notFoundEl.textContent = data.message;
                contentEl.classList.add("hidden");
                return;
            }

            notFoundEl.classList.add("hidden");
            contentEl.classList.remove("hidden");

            mapController.renderTrajectory(data.waypoints, data.summary);

            const sum = data.summary;
            document.getElementById("traj-plate-title").textContent = sum.plate_number;
            document.getElementById("traj-vehicle-type").textContent = sum.vehicle_type;
            document.getElementById("traj-total-dist").textContent = `${sum.total_distance_km} km`;
            document.getElementById("traj-avg-speed").textContent = `${sum.avg_speed_kmh} km/h`;
            document.getElementById("traj-elapsed-time").textContent = `${sum.total_elapsed_minutes} mins`;
            document.getElementById("traj-total-sightings").textContent = `${sum.total_sightings} Nodes`;

            const anomalyBanner = document.getElementById("traj-anomaly-banner");
            if (sum.anomaly_count > 0) {
                anomalyBanner.classList.remove("hidden");
                document.getElementById("traj-anomaly-text").textContent = `${sum.anomaly_count} Trajectory Anomalies Detected! ${sum.anomalies[0].calculated_speed_kmh} km/h between checkpoints.`;
            } else {
                anomalyBanner.classList.add("hidden");
            }

            const blacklistTag = document.getElementById("traj-blacklist-tag");
            if (sum.is_blacklisted) {
                blacklistTag.classList.remove("hidden");
                blacklistTag.textContent = `🚨 WATCHLIST: ${sum.blacklist_info.category} (${sum.blacklist_info.severity})`;
            } else {
                blacklistTag.classList.add("hidden");
            }

            const exportBtn = document.getElementById("btn-export-dossier");
            if (exportBtn) {
                exportBtn.onclick = () => {
                    window.open(`/api/export-dossier/${encodeURIComponent(sum.plate_number)}`, '_blank');
                };
            }

            this.renderSpatioTemporalSequence(data.waypoints);

        } catch (e) {
            console.error("Trajectory search error", e);
        }
    }

    renderSpatioTemporalSequence(waypoints) {
        const container = document.getElementById("trajectory-timeline") || document.getElementById("traj-timeline-list");
        if (!container) return;

        if (!waypoints || waypoints.length === 0) {
            container.innerHTML = `
                <div class="p-6 text-center text-xs text-slate-400 bg-slate-900/60 rounded-xl border border-slate-800">
                    No trajectory observations available for this vehicle.
                </div>
            `;
            return;
        }

        // Sort chronologically by timestamp
        const sorted = [...waypoints].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        let html = "";
        sorted.forEach((wp, idx) => {
            const isAnomaly = wp.is_anomaly;
            const obsStatus = wp.status || (wp.is_inferred ? "INFERRED" : wp.is_predicted ? "PREDICTED" : "OBSERVED");
            const statusBadge = obsStatus === "INFERRED"
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : obsStatus === "PREDICTED"
                ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";

            const ocrPct = wp.ocr_conf ? Math.round(wp.ocr_conf * 100) : 92;
            const timeStr = wp.timestamp ? (wp.timestamp.includes(' ') ? wp.timestamp.split(' ')[1] : wp.timestamp) : '--:--:--';
            const durationStr = wp.leg_duration_seconds ? `+${Math.round(wp.leg_duration_seconds / 60)}m` : 'First Sighting';

            html += `
                <div class="relative pl-6 pb-6 border-l-2 ${isAnomaly ? 'border-red-500' : 'border-slate-800'} last:border-transparent">
                    <div class="absolute -left-[9px] top-0 w-4 h-4 rounded-full ${isAnomaly ? 'bg-red-500 ring-4 ring-red-950 animate-pulse' : 'bg-cyan-500 ring-4 ring-cyan-950'} flex items-center justify-center text-[10px] font-bold text-black font-mono">
                        ${idx + 1}
                    </div>
                    <div class="bg-slate-900/80 p-3.5 rounded-xl border ${isAnomaly ? 'border-red-500/60 bg-red-950/20' : 'border-slate-800'} space-y-2">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-2">
                                <span class="font-mono font-bold text-xs text-cyan-300">${timeStr}</span>
                                <span class="text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${statusBadge}">${obsStatus}</span>
                            </div>
                            <span class="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/40">${wp.camera_id}</span>
                        </div>
                        <div>
                            <div class="font-bold text-xs text-slate-200">${wp.camera_name}</div>
                            <div class="text-[11px] text-slate-400 mt-0.5">${wp.sector} &bull; Direction: <strong class="text-slate-300">${wp.direction || 'Standard Flow'}</strong></div>
                        </div>
                        <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/60 text-[11px]">
                            <div><span class="text-slate-500">Transit:</span> <strong class="text-slate-300 font-mono">${durationStr}</strong></div>
                            <div><span class="text-slate-500">Dist:</span> <strong class="text-slate-300 font-mono">${wp.leg_distance_km || 0} km</strong></div>
                            <div><span class="text-slate-500">Speed:</span> <strong class="text-slate-300 font-mono">${wp.leg_speed_kmh || wp.instant_speed_kmh || 0} km/h</strong></div>
                        </div>
                        <div class="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                            <span>OCR Quality: <strong class="text-emerald-400">${ocrPct}%</strong></span>
                            <span>Plate: <strong class="font-mono text-slate-300">${wp.plate_number || document.getElementById("traj-search-input").value}</strong></span>
                        </div>
                        ${isAnomaly ? `<div class="mt-2 p-1.5 rounded bg-red-950/80 border border-red-600 text-red-200 text-[10px] font-semibold">⚠️ ${wp.anomaly_reason}</div>` : ''}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    renderTimeline(waypoints) {
        this.renderSpatioTemporalSequence(waypoints);
    }

    async loadAnalyticsTab() {
        try {
            const [heatRes, trendsRes, speedRes, densityRes] = await Promise.all([
                fetch("/api/analytics/heatmap").then(r => r.json()).catch(() => null),
                fetch("/api/analytics/hourly-volume").then(r => r.json()).catch(() => null),
                fetch("/api/analytics/speed-distribution").then(r => r.json()).catch(() => null),
                fetch("/api/analytics/camera-density").then(r => r.json()).catch(() => null)
            ]);

            if (heatRes) {
                mapController.renderHeatmap(heatRes.heatmap_points || [], heatRes.camera_nodes || []);
            }

            if (trendsRes && trendsRes.hours) {
                const hours = trendsRes.hours.map(h => h.hour);
                const counts = trendsRes.hours.map(h => h.count);
                analyticsCharts.renderHourlyVolume(hours, counts);
            }

            if (speedRes && speedRes.bins) {
                const speedDist = {};
                speedRes.bins.forEach(b => { speedDist[b.range] = b.count; });
                analyticsCharts.renderSpeedDistribution(speedDist);
            }

            if (densityRes && densityRes.cameras) {
                const camDensity = densityRes.cameras.map(c => ({
                    id: c.camera_id,
                    name: c.location.replace(" Square", "").replace(" Interchange", "").replace(" Flyover", ""),
                    count: c.vehicle_count
                }));
                analyticsCharts.renderCameraTraffic(camDensity);
            }

            setTimeout(() => {
                mapController.invalidateSize();
                analyticsCharts.resizeCharts();
            }, 100);

        } catch (e) {
            console.error("Traffic Analytics API Error:", e);
        }
    }

    async loadBlacklist() {
        try {
            const res = await fetch("/api/blacklist");
            const list = await res.json();
            const tbody = document.getElementById("blacklist-table-body");
            if (!tbody) return;

            tbody.innerHTML = "";
            list.forEach(item => {
                const tr = document.createElement("tr");
                tr.className = "border-b border-slate-800/60 hover:bg-slate-800/40 text-xs";
                const sevBadge = item.severity === 'CRITICAL'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                    : item.severity === 'HIGH'
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                    : 'bg-sky-500/20 text-sky-400 border border-sky-500/40';

                tr.innerHTML = `
                    <td class="py-3 px-4 font-mono font-bold text-amber-400">${item.plate_number}</td>
                    <td class="py-3 px-4 text-slate-300 font-medium">${item.reason || 'Security Watch'}</td>
                    <td class="py-3 px-4">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase ${sevBadge}">${item.severity || 'HIGH'}</span>
                    </td>
                    <td class="py-3 px-4 text-slate-400 font-mono text-[11px]">${item.date_added}</td>
                    <td class="py-3 px-4 text-right">
                        <button class="text-xs text-red-400 hover:text-red-300 font-semibold" onclick="app.removeBlacklist('${item.plate_number}')">
                            Remove
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error("Failed to load blacklist", e);
        }
    }

    async addBlacklist(event) {
        if (event) event.preventDefault();
        const plateEl = document.getElementById("bl-input-plate") || document.getElementById("bl-plate");
        const reasonEl = document.getElementById("bl-input-reason") || document.getElementById("bl-reason");
        const severityEl = document.getElementById("bl-input-severity") || document.getElementById("bl-severity");

        if (!plateEl || !reasonEl) {
            console.error("Watchlist form elements not found in DOM");
            return;
        }

        const rawPlate = plateEl.value.trim();
        const plate = rawPlate.toUpperCase().replace(/\s+/g, '');
        const reason = reasonEl.value.trim();
        const severity = severityEl ? severityEl.value : "HIGH";

        if (!plate) {
            alertsManager.showToast("Validation Error", "Please enter a valid registration plate number.", "HIGH");
            return;
        }

        if (!reason) {
            alertsManager.showToast("Validation Error", "Please enter a watch reason description.", "HIGH");
            return;
        }

        try {
            const res = await fetch("/api/blacklist", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    plate_number: plate,
                    category: "SUSPICIOUS",
                    severity: severity,
                    reason: reason
                })
            });

            const data = await res.json();

            if (res.ok || res.status === 200 || res.status === 201 || res.status === 210) {
                alertsManager.showToast("Priority Watchlist Registered", `${plate} registered on Priority Watchlist.`, "HIGH");
                plateEl.value = "";
                reasonEl.value = "";
                await this.loadBlacklist();
            } else if (res.status === 409) {
                alertsManager.showToast("Watchlist Warning", data.detail || `Vehicle ${plate} already exists in watchlist.`, "HIGH");
            } else {
                alertsManager.showToast("Registration Failed", data.detail || "Could not save watchlist record.", "HIGH");
            }
        } catch (e) {
            console.error("Add blacklist error", e);
            alertsManager.showToast("System Error", "Could not connect to Watchlist API.", "HIGH");
        }
    }

    async removeBlacklist(plate) {
        if (!confirm(`Remove plate ${plate} from security watchlist?`)) return;
        try {
            await fetch(`/api/blacklist/${encodeURIComponent(plate)}`, { method: "DELETE" });
            this.loadBlacklist();
            alertsManager.showToast("Watchlist Updated", `Plate ${plate} removed from watchlist`, "INFO");
        } catch (e) {
            console.error("Remove blacklist error", e);
        }
    }

    async loadRecentAlerts() {
        try {
            const res = await fetch("/api/alerts?limit=20");
            const alerts = await res.json();
            const container = document.getElementById("recent-alerts-list") || document.getElementById("security-alerts-list");
            if (!container) return;

            container.innerHTML = "";
            alerts.forEach(a => {
                const card = document.createElement("div");
                card.className = `p-4 rounded-xl border flex items-start justify-between ${
                    a.severity === 'CRITICAL' ? 'bg-red-950/30 border-red-500/40' : 'bg-amber-950/30 border-amber-500/40'
                }`;
                card.innerHTML = `
                    <div class="flex items-start space-x-3">
                        <div class="p-2 rounded-lg ${a.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}">
                            <i data-lucide="alert-triangle" class="w-5 h-5"></i>
                        </div>
                        <div>
                            <div class="flex items-center space-x-2">
                                <span class="font-mono font-bold text-sm text-slate-100">${a.plate_number}</span>
                                <span class="text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                                    a.severity === 'CRITICAL' ? 'bg-red-600 text-white' : 'bg-amber-600 text-white'
                                }">${a.alert_type}</span>
                                ${a.acknowledged ? '<span class="text-[10px] text-emerald-400 font-semibold">✓ ACKNOWLEDGED</span>' : ''}
                            </div>
                            <p class="text-xs text-slate-300 mt-1">${a.description}</p>
                            <div class="text-[11px] text-slate-500 mt-1 font-mono">${a.timestamp} &bull; Node ${a.camera_id}</div>
                        </div>
                    </div>
                    ${!a.acknowledged ? `
                        <button class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700" onclick="app.acknowledgeAlert(${a.id}, this)">
                            Acknowledge
                        </button>
                    ` : ''}
                `;
                container.appendChild(card);
            });
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error("Failed to load alerts", e);
        }
    }

    async acknowledgeAlert(alertId, btn) {
        try {
            await fetch(`/api/alerts/${alertId}/acknowledge`, { method: "POST" });
            if (btn) {
                btn.parentElement.classList.add("opacity-60");
                btn.remove();
            }
            this.loadKPIs();
        } catch (e) {
            console.error("Acknowledge alert error", e);
        }
    }

    renderInfrastructureTable() {
        const tbody = document.getElementById("infra-table-body");
        if (!tbody) return;

        tbody.innerHTML = "";
        this.cameras.forEach(cam => {
            const tr = document.createElement("tr");
            tr.className = "border-b border-slate-800/60 hover:bg-slate-800/40 text-xs";
            tr.innerHTML = `
                <td class="py-3 px-4 font-mono font-bold text-cyan-400">${cam.id}</td>
                <td class="py-3 px-4 text-slate-200 font-semibold">${cam.name}</td>
                <td class="py-3 px-4 text-slate-400">${cam.sector}</td>
                <td class="py-3 px-4 text-slate-300">${cam.direction}</td>
                <td class="py-3 px-4 font-mono text-[11px] text-slate-400">${cam.lat.toFixed(4)} N, ${cam.lng.toFixed(4)} E</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
                        cam.status === 'ONLINE' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-red-500/20 text-red-400 border border-red-500/40'
                    }">${cam.status}</span>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    async inspectUploadedVideo(file) {
        const resultContainer = document.getElementById("inspector-results");
        const resultImg = document.getElementById("inspector-annotated-img");
        const platesList = document.getElementById("inspector-detected-plates");

        const formData = new FormData();
        formData.append("file", file);

        alertsManager.showToast("Video ANPR Analysis", `Analyzing video ${file.name} with YOLO plate detector...`, "INFO");

        try {
            const res = await fetch("/api/anpr/inspect-video", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (!data.success) {
                alert("Video processing failed: " + (data.detail || "Unknown error"));
                return;
            }

            resultContainer.classList.remove("hidden");
            if (data.snapshot_url) {
                resultImg.src = data.snapshot_url + "?t=" + Date.now();
            }

            platesList.innerHTML = "";
            if (!data.plates_detected || data.plates_detected.length === 0) {
                platesList.innerHTML = `<div class="text-xs text-amber-400 p-2 bg-amber-950/40 rounded border border-amber-800">Video analyzed (${data.frames_processed} frames sample): No valid Indian plates detected.</div>`;
            } else {
                let html = `<div class="text-[11px] text-slate-400 mb-2 font-mono">Analyzed <strong>${data.total_video_frames}</strong> video frames (${data.frames_processed} sampled). Found <strong>${data.total_plates_detected}</strong> plate detections:</div>`;
                data.plates_detected.forEach(p => {
                    html += `
                        <div class="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between mb-2">
                            <div>
                                <div class="text-[10px] text-slate-400 uppercase font-bold">Plate @ ${p.timestamp_offset_sec}s</div>
                                <div class="text-lg font-black font-mono text-cyan-300 tracking-wider">${p.plate_number}</div>
                                <div class="text-[11px] text-slate-400 mt-0.5">YOLO: <strong>${Math.round(p.detection_conf*100)}%</strong> &bull; OCR: <strong>${Math.round(p.ocr_conf*100)}%</strong></div>
                            </div>
                            <button class="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs" onclick="app.searchTrajectory('${p.plate_number}'); app.switchTab('trajectory')">
                                Track Trajectory →
                            </button>
                        </div>
                    `;
                });
                platesList.innerHTML = html;
            }

            alertsManager.showToast("Video ANPR Complete", `Processed ${data.frames_processed} frames. Found ${data.total_plates_detected} plate(s)!`, "INFO");
            this.loadRecentDetections();
            this.loadKPIs();
        } catch (e) {
            console.error("Inspect video error", e);
            alert("Error running Video ANPR: " + e);
        }
    }

    async toggleCameraWebcam(camId) {
        const select = document.getElementById(`webcam-device-${camId}`);
        const btnText = document.getElementById(`btn-text-${camId}`);
        const btn = document.getElementById(`btn-webcam-${camId}`);
        const badge = document.getElementById(`badge-${camId}`);
        const dot = document.getElementById(`dot-${camId}`);
        const img = document.getElementById(`feed-img-${camId}`);

        const devIndex = select ? parseInt(select.value, 10) : 0;
        const isCurrentlyConnected = btnText && btnText.textContent.includes("Disconnect");

        if (isCurrentlyConnected) {
            // Disconnect webcam
            alertsManager.showToast("Disconnecting Webcam", `Disconnecting webcam from ${camId}...`, "INFO");
            try {
                const res = await fetch(`/api/cameras/${camId}/disconnect-webcam`, { method: "POST" });
                if (btnText) btnText.textContent = "Connect Webcam";
                if (btn) btn.className = "px-2 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white font-bold text-[11px] flex items-center space-x-1";
                if (badge) { badge.textContent = "OFFLINE"; badge.className = "op-badge opacity-70"; }
                if (dot) dot.className = "status-dot offline";
                if (img) img.src = `/api/video-feed/${camId}?t=` + Date.now();
                alertsManager.showToast("Webcam Offline", `Webcam disconnected from ${camId}.`, "INFO");
            } catch (e) {
                console.error("Disconnect error", e);
            }
        } else {
            // Connect webcam
            alertsManager.showToast("Connecting Webcam", `Attempting to open Webcam Device ${devIndex} for ${camId}...`, "INFO");
            try {
                const res = await fetch(`/api/cameras/${camId}/connect-webcam`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ device_index: devIndex })
                });
                const data = await res.json();
                if (!res.ok) {
                    alert(`Failed to connect Webcam ${devIndex} to ${camId}:\n\n` + (data.detail || data.message || "Device could not be opened. Ensure camera is plugged into your PC."));
                    return;
                }
                if (btnText) btnText.textContent = "Disconnect";
                if (btn) btn.className = "px-2 py-1 rounded bg-red-600 hover:bg-red-500 text-white font-bold text-[11px] flex items-center space-x-1";
                if (badge) { badge.textContent = "WEBCAM LIVE"; badge.className = "op-badge op-badge-online"; }
                if (dot) dot.className = "status-dot online";
                if (img) img.src = `/api/video-feed/${camId}?t=` + Date.now();
                alertsManager.showToast("Webcam Connected", `Webcam Device ${devIndex} streaming LIVE on ${camId} with ANPR!`, "HIGH");
            } catch (e) {
                console.error("Connect webcam error", e);
                alert(`Error connecting Webcam ${devIndex} to ${camId}: ` + e);
            }
        }
    }

    toggleAllCameraFeeds() {
        const cams = ["CAM-01", "CAM-02", "CAM-03", "CAM-04"];
        cams.forEach(camId => {
            const img = document.getElementById(`feed-img-${camId}`);
            if (img) {
                img.src = `/api/video-feed/${camId}?t=` + Date.now();
            }
        });
        alertsManager.showToast("Surveillance Grid Online", "Live video feed streams connecting for all 4 Nagpur camera nodes...", "HIGH");
    }

    setupEventListeners() {
        const input = document.getElementById("traj-search-input");
        if (input) {
            input.addEventListener("keyup", (e) => {
                if (e.key === "Enter") this.searchTrajectory();
            });
        }

        document.querySelectorAll(".quick-plate-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                this.searchTrajectory(btn.dataset.plate);
            });
        });

        const predInput = document.getElementById("predictive-search-input");
        if (predInput) {
            predInput.addEventListener("keyup", (e) => {
                if (e.key === "Enter") this.searchPredictiveHandoff();
            });
        }

        document.querySelectorAll(".quick-pred-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                this.searchPredictiveHandoff(btn.dataset.plate);
            });
        });

        const blForm = document.getElementById("add-blacklist-form");
        if (blForm) {
            blForm.addEventListener("submit", (e) => this.addBlacklist(e));
        }

        const audioBtn = document.getElementById("btn-toggle-audio");
        if (audioBtn) {
            audioBtn.addEventListener("click", () => {
                alertsManager.soundEnabled = !alertsManager.soundEnabled;
                audioBtn.innerHTML = alertsManager.soundEnabled
                    ? `<i data-lucide="volume-2" class="w-4 h-4"></i>`
                    : `<i data-lucide="volume-x" class="w-4 h-4 text-slate-500"></i>`;
                if (window.lucide) lucide.createIcons();
            });
        }

        const themeBtn = document.getElementById("btn-toggle-theme");
        if (themeBtn) {
            themeBtn.addEventListener("click", () => this.toggleTheme());
        }

        const webcamBtn = document.getElementById("btn-toggle-webcam");
        if (webcamBtn) {
            webcamBtn.addEventListener("click", () => this.toggleLiveWebcamStream());
        }

        const freeMapSelect = document.getElementById("free-map-theme-select");
        if (freeMapSelect) {
            freeMapSelect.value = mapController.currentTheme || "carto-dark";
            freeMapSelect.addEventListener("change", (e) => {
                const selectedTheme = e.target.value;
                mapController.setMapTheme(selectedTheme);
                alertsManager.showToast("Map Theme Updated", `Switched Nagpur map to 100% Free ${e.target.options[e.target.selectedIndex].text}`, "INFO");
            });
        }

        // Image upload inspector
        const fileInput = document.getElementById("anpr-file-upload");
        if (fileInput) {
            fileInput.addEventListener("change", (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.inspectUploadedImage(e.target.files[0]);
                }
            });
        }

        // Video upload inspector
        const videoInput = document.getElementById("anpr-video-upload");
        if (videoInput) {
            videoInput.addEventListener("change", (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.inspectUploadedVideo(e.target.files[0]);
                }
            });
        }
    }
}

const app = new App();
window.app = app;
document.addEventListener("DOMContentLoaded", () => {
    app.init();
    if (window.lucide) lucide.createIcons();
});
