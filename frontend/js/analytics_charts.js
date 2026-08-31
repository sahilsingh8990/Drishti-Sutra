// Analytics Chart.js and Data Visualizations
class AnalyticsCharts {
    constructor() {
        this.hourlyChart = null;
        this.speedChart = null;
        this.cameraTrafficChart = null;
    }

    renderHourlyVolume(hours, volumes) {
        const ctx = document.getElementById("chart-volume") || document.getElementById("hourly-volume-chart");
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

    renderSpeedDistribution(speedDist) {
        const ctx = document.getElementById("chart-speed") || document.getElementById("vehicle-type-chart");
        if (!ctx) return;

        if (this.speedChart) {
            this.speedChart.destroy();
        }

        const labels = Object.keys(speedDist || {});
        const data = Object.values(speedDist || {});
        const colors = ['#ef4444', '#f59e0b', '#10b981', '#06b6d4'];

        this.speedChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Vehicle Count',
                    data: data,
                    backgroundColor: colors,
                    borderRadius: 6,
                    borderWidth: 0
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
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
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

    renderCameraTraffic(cameraData) {
        const ctx = document.getElementById("chart-camera-traffic");
        if (!ctx) return;

        if (this.cameraTrafficChart) {
            this.cameraTrafficChart.destroy();
        }

        const labels = (cameraData || []).map(c => `${c.id} (${c.name})`);
        const data = (cameraData || []).map(c => c.count);

        this.cameraTrafficChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Detections',
                    data: data,
                    backgroundColor: 'rgba(56, 189, 248, 0.75)',
                    borderColor: '#38bdf8',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
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
                        ticks: { color: '#64748b', font: { size: 10 } },
                        beginAtZero: true
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { size: 9 } }
                    }
                }
            }
        });
    }

    resizeCharts() {
        if (this.hourlyChart) this.hourlyChart.resize();
        if (this.speedChart) this.speedChart.resize();
        if (this.cameraTrafficChart) this.cameraTrafficChart.resize();
    }

    updateTheme(theme) {
        const isLight = theme === 'light';
        const gridColor = isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(255, 255, 255, 0.05)';
        const tickColor = isLight ? '#475569' : '#64748b';
        const labelColor = isLight ? '#1e293b' : '#94a3b8';
        const tooltipBg = isLight ? '#ffffff' : '#0f172a';
        const tooltipBorder = isLight ? '#cbd5e1' : '#334155';

        [this.hourlyChart, this.speedChart, this.cameraTrafficChart].forEach(chart => {
            if (chart && chart.options) {
                if (chart.options.plugins && chart.options.plugins.tooltip) {
                    chart.options.plugins.tooltip.backgroundColor = tooltipBg;
                    chart.options.plugins.tooltip.borderColor = tooltipBorder;
                }
                if (chart.options.scales) {
                    if (chart.options.scales.x) {
                        if (chart.options.scales.x.grid && chart.options.scales.x.grid.display !== false) {
                            chart.options.scales.x.grid.color = gridColor;
                        }
                        if (chart.options.scales.x.ticks) chart.options.scales.x.ticks.color = labelColor;
                    }
                    if (chart.options.scales.y) {
                        if (chart.options.scales.y.grid && chart.options.scales.y.grid.display !== false) {
                            chart.options.scales.y.grid.color = gridColor;
                        }
                        if (chart.options.scales.y.ticks) chart.options.scales.y.ticks.color = tickColor;
                    }
                }
                chart.update();
            }
        });
    }
}

const analyticsCharts = new AnalyticsCharts();

