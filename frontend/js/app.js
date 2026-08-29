// Main Frontend Application Controller
class App {
    constructor() {
        this.currentTab = 'live';
        this.ws = null;
        this.cameras = [];
    }

    async init() {
        // Initialize clock
        this.startClock();

        // Initialize maps
        mapController.initMaps();

        // Setup tabs
        this.setupTabNavigation();

        // Connect WebSockets
        this.connectWebSocket();

        // Load initial data
        await this.loadCameras();
        await this.loadKPIs();
        await this.loadRecentDetections();
        await this.loadRecentAlerts();

        // Setup search & buttons
        this.setupEventListeners();

        // Load initial trajectory for demo (e.g. DL01CA1234)
        this.searchTrajectory("DL01CA1234");
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

        // Update button active state
        document.querySelectorAll(".tab-btn").forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.className = "tab-btn px-4 py-2.5 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-lg shadow-cyan-950/50";
            } else {
                btn.className = "tab-btn px-4 py-2.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60";
            }
        });

        // Toggle sections
        document.querySelectorAll(".tab-content").forEach(section => {
            if (section.id === `tab-${tabName}`) {
                section.classList.remove("hidden");
            } else {
                section.classList.add("hidden");
            }
        });

        // Trigger map resizes
        mapController.invalidateSize();

        // Refresh tab-specific data
        if (tabName === "analytics") {
            this.loadAnalyticsTab();
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
                }
            } catch (e) {
                console.error("WS Parse error", e);
            }
        };

        this.ws.onclose = () => {
            console.warn("WebSocket disconnected. Retrying in 3s...");
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

    handleNewDetection(detection) {
        // Prepend to live ticker
        const ticker = document.getElementById("live-detection-ticker");
        if (ticker) {
            const card = document.createElement("div");
            card.className = "p-3 bg-slate-900/80 rounded-xl border border-slate-800 hover:border-cyan-500/50 transition-all transform hover:-translate-y-0.5 duration-200 flex items-center justify-between";
            
            const isBlacklisted = detection.is_blacklisted;
            const plateBg = isBlacklisted ? "bg-red-500/20 text-red-400 border-red-500/50" : "bg-cyan-500/10 text-cyan-300 border-cyan-500/30";

            card.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="w-9 h-9 rounded-lg bg-slate-800/80 flex items-center justify-center text-slate-300 font-mono text-xs">
                        ${detection.camera_id.replace('CAM-', '#')}
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-mono font-extrabold text-sm tracking-wide px-2 py-0.5 rounded border ${plateBg}">${detection.plate_number}</span>
                            ${isBlacklisted ? '<span class="text-[9px] bg-red-600 text-white font-bold px-1.5 py-0.2 rounded uppercase animate-pulse">FLAGGED</span>' : ''}
                        </div>
                        <div class="text-[11px] text-slate-400 mt-1">${detection.camera_name} &bull; <span class="text-slate-500">${detection.sector}</span></div>
                    </div>
                </div>
                <div class="text-right text-xs">
                    <div class="font-mono font-bold text-slate-300">${detection.speed_kmh} km/h</div>
                    <div class="text-[10px] text-slate-500 mt-0.5">${detection.timestamp.split(' ')[1]}</div>
                </div>
            `;

            ticker.insertBefore(card, ticker.firstChild);
            if (ticker.children.length > 25) {
                ticker.lastChild.remove();
            }
        }

        // Increment today's vehicle count KPI
        const totalEl = document.getElementById("kpi-total-detections");
        if (totalEl) {
            const curr = parseInt(totalEl.textContent) || 0;
            totalEl.textContent = (curr + 1).toLocaleString();
        }

        alertsManager.playAlertTone("detection");
    }

    handleSecurityAlert(alert) {
        alertsManager.showToast(
            alert.alert_type === "CLONED_PLATE" ? "CLONED PLATE ANOMALY" : "SECURITY TARGET DETECTED",
            alert.description,
            alert.severity || "CRITICAL"
        );

        // Update active alerts KPI
        const alertsKpi = document.getElementById("kpi-active-alerts");
        if (alertsKpi) {
            const curr = parseInt(alertsKpi.textContent) || 0;
            alertsKpi.textContent = curr + 1;
        }

        // Show banner in Live tab
        const banner = document.getElementById("urgent-alert-banner");
        if (banner) {
            banner.classList.remove("hidden");
            document.getElementById("urgent-alert-text").textContent = alert.description;
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

            // Render Trajectory on GIS Map
            mapController.renderTrajectory(data.waypoints, data.summary);

            // Populate Summary Info
            const sum = data.summary;
            document.getElementById("traj-plate-title").textContent = sum.plate_number;
            document.getElementById("traj-vehicle-type").textContent = sum.vehicle_type;
            document.getElementById("traj-total-dist").textContent = `${sum.total_distance_km} km`;
            document.getElementById("traj-avg-speed").textContent = `${sum.avg_speed_kmh} km/h`;
            document.getElementById("traj-elapsed-time").textContent = `${sum.total_elapsed_minutes} mins`;
            document.getElementById("traj-total-sightings").textContent = `${sum.total_sightings} Nodes`;

            // Anomaly Badge
            const anomalyBanner = document.getElementById("traj-anomaly-banner");
            if (sum.anomaly_count > 0) {
                anomalyBanner.classList.remove("hidden");
                document.getElementById("traj-anomaly-text").textContent = `${sum.anomaly_count} Trajectory Anomalies Detected! ${sum.anomalies[0].calculated_speed_kmh} km/h between checkpoints.`;
            } else {
                anomalyBanner.classList.add("hidden");
            }

            // Blacklist Flag
            const blacklistTag = document.getElementById("traj-blacklist-tag");
            if (sum.is_blacklisted) {
                blacklistTag.classList.remove("hidden");
                blacklistTag.textContent = `🚨 WATCHLIST: ${sum.blacklist_info.category} (${sum.blacklist_info.severity})`;
            } else {
                blacklistTag.classList.add("hidden");
            }

            // Setup Export Dossier Button
            const exportBtn = document.getElementById("btn-export-dossier");
            if (exportBtn) {
                exportBtn.onclick = () => {
                    window.open(`/api/export-dossier/${encodeURIComponent(sum.plate_number)}`, '_blank');
                };
            }

            // Render Timeline List
            this.renderTimeline(data.waypoints);

        } catch (e) {
            console.error("Trajectory search error", e);
        }
    }

    renderTimeline(waypoints) {
        const container = document.getElementById("traj-timeline-list");
        if (!container) return;

        let html = "";
        waypoints.forEach(wp => {
            const isAnomaly = wp.is_anomaly;
            html += `
                <div class="relative pl-6 pb-6 border-l-2 ${isAnomaly ? 'border-red-500' : 'border-slate-800'} last:border-transparent">
                    <div class="absolute -left-[9px] top-0 w-4 h-4 rounded-full ${isAnomaly ? 'bg-red-500 ring-4 ring-red-950 animate-pulse' : 'bg-cyan-500 ring-4 ring-cyan-950'} flex items-center justify-center text-[10px] font-bold text-black font-mono">
                        ${wp.step}
                    </div>
                    <div class="bg-slate-900/80 p-3 rounded-xl border ${isAnomaly ? 'border-red-500/60 bg-red-950/20' : 'border-slate-800'}">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-xs text-slate-200">${wp.camera_name}</span>
                            <span class="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/40">${wp.camera_id}</span>
                        </div>
                        <div class="text-[11px] text-slate-400 mt-0.5">${wp.sector} &bull; ${wp.direction}</div>
                        <div class="grid grid-cols-3 gap-2 mt-2 pt-2 border-t border-slate-800/60 text-[11px]">
                            <div><span class="text-slate-500">Time:</span> <strong class="text-slate-300 font-mono">${wp.timestamp.split(' ')[1]}</strong></div>
                            <div><span class="text-slate-500">Speed:</span> <strong class="text-slate-300 font-mono">${wp.leg_speed_kmh} km/h</strong></div>
                            <div><span class="text-slate-500">Dist:</span> <strong class="text-slate-300 font-mono">${wp.leg_distance_km} km</strong></div>
                        </div>
                        ${isAnomaly ? `<div class="mt-2 p-1.5 rounded bg-red-950/80 border border-red-600 text-red-200 text-[10px] font-semibold">⚠️ ${wp.anomaly_reason}</div>` : ''}
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    async loadAnalyticsTab() {
        try {
            const [heatRes, odRes, congRes, trendsRes] = await Promise.all([
                fetch("/api/analytics/heatmap").then(r => r.json()),
                fetch("/api/analytics/od-matrix").then(r => r.json()),
                fetch("/api/analytics/congestion").then(r => r.json()),
                fetch("/api/analytics/hourly-trends").then(r => r.json())
            ]);

            // Heatmap
            mapController.renderHeatmap(heatRes.heatmap_points, heatRes.camera_nodes);

            // 24h Volume Chart
            analyticsCharts.renderHourlyVolume(trendsRes.hours, trendsRes.volumes);

            // Vehicle Types
            analyticsCharts.renderVehicleTypes(trendsRes.vehicle_types);

            // OD Corridors
            analyticsCharts.renderODCorridors(odRes.top_corridors);

            // Bottlenecks
            analyticsCharts.renderBottlenecks(congRes);

        } catch (e) {
            console.error("Failed to load analytics tab", e);
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
                tr.innerHTML = `
                    <td class="py-3 px-4 font-mono font-bold text-amber-400">${item.plate_number}</td>
                    <td class="py-3 px-4">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            item.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/40' : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                        }">${item.category}</span>
                    </td>
                    <td class="py-3 px-4 text-slate-300">${item.reason}</td>
                    <td class="py-3 px-4 text-slate-400">${item.date_added}</td>
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
        event.preventDefault();
        const plate = document.getElementById("bl-plate").value;
        const category = document.getElementById("bl-category").value;
        const severity = document.getElementById("bl-severity").value;
        const reason = document.getElementById("bl-reason").value;

        try {
            const res = await fetch("/api/blacklist", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ plate_number: plate, category, severity, reason })
            });
            if (res.ok) {
                alertsManager.showToast("Blacklist Updated", `Plate ${plate} added to watchlist`, "HIGH");
                document.getElementById("add-blacklist-modal").classList.add("hidden");
                document.getElementById("add-blacklist-form").reset();
                this.loadBlacklist();
            }
        } catch (e) {
            console.error("Add blacklist error", e);
        }
    }

    async removeBlacklist(plate) {
        if (!confirm(`Remove plate ${plate} from security watchlist?`)) return;
        try {
            await fetch(`/api/blacklist/${encodeURIComponent(plate)}`, { method: "DELETE" });
            this.loadBlacklist();
            alertsManager.showToast("Removed", `Plate ${plate} removed from watchlist`, "INFO");
        } catch (e) {
            console.error("Remove blacklist error", e);
        }
    }

    async loadRecentAlerts() {
        try {
            const res = await fetch("/api/alerts?limit=20");
            const alerts = await res.json();
            const container = document.getElementById("security-alerts-list");
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

    setupEventListeners() {
        // Trajectory Search input Enter key
        const input = document.getElementById("traj-search-input");
        if (input) {
            input.addEventListener("keyup", (e) => {
                if (e.key === "Enter") this.searchTrajectory();
            });
        }

        // Quick Search buttons
        document.querySelectorAll(".quick-plate-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                this.searchTrajectory(btn.dataset.plate);
            });
        });

        // Add Blacklist Form
        const blForm = document.getElementById("add-blacklist-form");
        if (blForm) {
            blForm.addEventListener("submit", (e) => this.addBlacklist(e));
        }

        // Audio toggle button
        const audioBtn = document.getElementById("btn-toggle-audio");
        if (audioBtn) {
            audioBtn.addEventListener("click", () => {
                alertsManager.soundEnabled = !alertsManager.soundEnabled;
                audioBtn.innerHTML = alertsManager.soundEnabled
                    ? `<i data-lucide="volume-2" class="w-4 h-4"></i><span>Audio Alerts ON</span>`
                    : `<i data-lucide="volume-x" class="w-4 h-4 text-slate-500"></i><span class="text-slate-500">Audio Muted</span>`;
                if (window.lucide) lucide.createIcons();
            });
        }
    }
}

const app = new App();
document.addEventListener("DOMContentLoaded", () => {
    app.init();
    if (window.lucide) lucide.createIcons();
});
