// Analytics Chart.js and Data Visualizations
class AnalyticsCharts {
    constructor() {
        this.hourlyChart = null;
        this.speedChart = null;
        this.cameraTrafficChart = null;

        this.lastHourlyData = null;
        this.lastSpeedData = null;
        this.lastCameraData = null;
    }

    getThemeColors() {
        const isLight = document.documentElement.classList.contains("theme-light") ||
                       document.body.classList.contains("theme-light") ||
                       (window.themeController && window.themeController.currentTheme === "light");

        return {
            isLight,
            gridColor: isLight ? 'rgba(6, 43, 74, 0.1)' : 'rgba(14, 68, 109, 0.4)',
            tickColor: isLight ? '#062B4A' : '#A1B3C4',
            labelColor: isLight ? '#062B4A' : '#F7F6F1',
            tooltipBg: isLight ? '#FFFFFF' : '#062B4A',
            tooltipText: isLight ? '#062B4A' : '#F7F6F1',
            tooltipBorder: isLight ? '#CBD3D8' : '#0E446D',
            volumeLineColor: '#13752F', // Forest Green Line
            volumePointColor: '#2E9147',
            volumeGrad1: isLight ? 'rgba(19, 117, 47, 0.35)' : 'rgba(19, 117, 47, 0.45)',
            volumeGrad2: 'rgba(19, 117, 47, 0.01)',
            speedColors: ['#13752F', '#2E9147', '#D98212', '#F6A126', '#0A3655', '#D83A3A'],
            cameraBarBg: 'rgba(19, 117, 47, 0.85)',
            cameraBarBorder: '#2E9147'
        };
    }

    renderHourlyVolume(hours, volumes) {
        this.lastHourlyData = { hours, volumes };
        const ctx = document.getElementById("chart-volume") || document.getElementById("hourly-volume-chart");
        if (!ctx || typeof Chart === 'undefined') return;

        if (this.hourlyChart) {
            this.hourlyChart.destroy();
            this.hourlyChart = null;
        }

        const colors = this.getThemeColors();
        const canvasCtx = ctx.getContext('2d');
        const gradient = canvasCtx.createLinearGradient(0, 0, 0, 260);
        gradient.addColorStop(0, colors.volumeGrad1);
        gradient.addColorStop(1, colors.volumeGrad2);

        this.hourlyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [{
                    label: 'Vehicle Throughput (Vehicles/Hr)',
                    data: volumes,
                    borderColor: colors.volumeLineColor,
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    pointBackgroundColor: colors.volumePointColor,
                    pointBorderColor: colors.isLight ? '#FFFFFF' : '#041F36',
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
                        backgroundColor: colors.tooltipBg,
                        titleColor: colors.tooltipText,
                        bodyColor: colors.tooltipText,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        padding: 10
                    }
                },
                scales: {
                    x: {
                        grid: { color: colors.gridColor },
                        ticks: { color: colors.tickColor, font: { size: 10, weight: 'bold' } }
                    },
                    y: {
                        grid: { color: colors.gridColor },
                        ticks: { color: colors.tickColor, font: { size: 10, weight: 'bold' } },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    renderSpeedDistribution(speedDist) {
        this.lastSpeedData = speedDist;
        const ctx = document.getElementById("chart-speed") || document.getElementById("vehicle-type-chart");
        if (!ctx || typeof Chart === 'undefined') return;

        if (this.speedChart) {
            this.speedChart.destroy();
            this.speedChart = null;
        }

        const colors = this.getThemeColors();
        const labels = Object.keys(speedDist || {});
        const data = Object.values(speedDist || {});

        this.speedChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Vehicle Count',
                    data: data,
                    backgroundColor: colors.speedColors,
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
                        backgroundColor: colors.tooltipBg,
                        titleColor: colors.tooltipText,
                        bodyColor: colors.tooltipText,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        padding: 10
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: colors.tickColor, font: { size: 10, weight: 'bold' } }
                    },
                    y: {
                        grid: { color: colors.gridColor },
                        ticks: { color: colors.tickColor, font: { size: 10, weight: 'bold' } },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    renderCameraTraffic(cameraData) {
        this.lastCameraData = cameraData;
        const ctx = document.getElementById("chart-camera-traffic");
        if (!ctx || typeof Chart === 'undefined') return;

        if (this.cameraTrafficChart) {
            this.cameraTrafficChart.destroy();
            this.cameraTrafficChart = null;
        }

        const colors = this.getThemeColors();
        const labels = (cameraData || []).map(c => `${c.id} (${c.name})`);
        const data = (cameraData || []).map(c => c.count);

        this.cameraTrafficChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Detections',
                    data: data,
                    backgroundColor: colors.cameraBarBg,
                    borderColor: colors.cameraBarBorder,
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
                        backgroundColor: colors.tooltipBg,
                        titleColor: colors.tooltipText,
                        bodyColor: colors.tooltipText,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        padding: 10
                    }
                },
                scales: {
                    x: {
                        grid: { color: colors.gridColor },
                        ticks: { color: colors.tickColor, font: { size: 10, weight: 'bold' } },
                        beginAtZero: true
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: colors.tickColor, font: { size: 9, weight: 'bold' } }
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
        if (this.lastHourlyData) {
            this.renderHourlyVolume(this.lastHourlyData.hours, this.lastHourlyData.volumes);
        }
        if (this.lastSpeedData) {
            this.renderSpeedDistribution(this.lastSpeedData);
        }
        if (this.lastCameraData) {
            this.renderCameraTraffic(this.lastCameraData);
        }
    }
}

const analyticsCharts = new AnalyticsCharts();
window.analyticsCharts = analyticsCharts;
