// Analytics Chart.js and Data Visualizations
class AnalyticsCharts {
    constructor() {
        this.hourlyChart = null;
        this.vehicleTypeChart = null;
    }

    renderHourlyVolume(hours, volumes) {
        const ctx = document.getElementById("hourly-volume-chart");
        if (!ctx) return;

        if (this.hourlyChart) {
            this.hourlyChart.destroy();
        }

        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(6, 182, 212, 0.45)');
        gradient.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

        this.hourlyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [{
                    label: 'Vehicle Throughput (Vehicles/Hr)',
                    data: volumes,
                    borderColor: '#06b6d4',
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    pointBackgroundColor: '#0891b2',
                    pointBorderColor: '#ffffff',
                    pointRadius: 3,
                    fill: true,
                    tension: 0.35
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        titleColor: '#38bdf8',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 10
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#64748b', font: { size: 10 } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#64748b', font: { size: 10 } },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    renderVehicleTypes(vtypes) {
        const ctx = document.getElementById("vehicle-type-chart");
        if (!ctx) return;

        if (this.vehicleTypeChart) {
            this.vehicleTypeChart.destroy();
        }

        const labels = Object.keys(vtypes);
        const data = Object.values(vtypes);
        const colors = ['#0284c7', '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];

        this.vehicleTypeChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#0f172a'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#94a3b8', boxWidth: 12, font: { size: 11 } }
                    }
                },
                cutout: '70%'
            }
        });
    }

    renderODCorridors(corridors) {
        const container = document.getElementById("od-corridors-list");
        if (!container) return;

        if (!corridors || corridors.length === 0) {
            container.innerHTML = `<div class="text-xs text-slate-500 text-center py-4">No OD corridor data yet.</div>`;
            return;
        }

        const maxVol = Math.max(...corridors.map(c => c.volume), 1);

        let html = "";
        corridors.forEach((c, idx) => {
            const pct = Math.round((c.volume / maxVol) * 100);
            html += `
                <div class="p-3 bg-slate-900/60 rounded-lg border border-slate-800/80">
                    <div class="flex items-center justify-between text-xs mb-1.5">
                        <div class="flex items-center space-x-1.5 font-medium text-slate-200">
                            <span class="text-cyan-400 font-bold">#${idx + 1}</span>
                            <span>${c.origin}</span>
                            <span class="text-slate-500">→</span>
                            <span class="text-emerald-400">${c.destination}</span>
                        </div>
                        <span class="font-mono font-bold text-cyan-300 text-xs">${c.volume} trips</span>
                    </div>
                    <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div class="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full rounded-full" style="width: ${pct}%"></div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    renderBottlenecks(bottlenecks) {
        const container = document.getElementById("bottlenecks-list");
        if (!container) return;

        if (!bottlenecks || bottlenecks.length === 0) {
            container.innerHTML = `<div class="text-xs text-slate-500 text-center py-4">No congestion detected.</div>`;
            return;
        }

        let html = "";
        bottlenecks.slice(0, 6).forEach((b) => {
            html += `
                <div class="p-3 bg-slate-900/60 rounded-lg border border-slate-800/80 flex items-center justify-between">
                    <div>
                        <div class="font-bold text-xs text-slate-200">${b.camera_name}</div>
                        <div class="text-[11px] text-slate-400 mt-0.5">${b.sector} (${b.camera_id})</div>
                        <div class="flex items-center space-x-3 text-[11px] text-slate-400 mt-1">
                            <span>Vol: <strong class="text-slate-200 font-mono">${b.total_vehicles}</strong></span>
                            <span>Avg Spd: <strong class="text-slate-200 font-mono">${b.avg_speed} km/h</strong></span>
                        </div>
                    </div>
                    <div class="text-right">
                        <span class="inline-block px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${b.badge}">
                            ${b.level}
                        </span>
                        <div class="text-[10px] text-slate-400 mt-1">Risk Score: <strong class="text-slate-200">${b.risk_score}%</strong></div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }
}

const analyticsCharts = new AnalyticsCharts();
