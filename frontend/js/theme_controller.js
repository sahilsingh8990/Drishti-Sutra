// ============================================================
// DRISHTI-SUTRA INTEGRATED TRAFFIC COMMAND CENTRE (ICCC)
// Centralized Theme Controller (Dark <-> Light Brand Tokens)
// ============================================================

class ThemeController {
    constructor() {
        this.STORAGE_KEY = "drishti-sutra-theme";
        this.currentTheme = localStorage.getItem(this.STORAGE_KEY) || localStorage.getItem("drishti_theme") || "dark";
    }

    initTheme() {
        const savedTheme = localStorage.getItem(this.STORAGE_KEY) || localStorage.getItem("drishti_theme") || "dark";
        this.setTheme(savedTheme, false);
    }

    setTheme(theme, notify = true) {
        if (theme !== "dark" && theme !== "light") {
            theme = "dark";
        }

        this.currentTheme = theme;
        localStorage.setItem(this.STORAGE_KEY, theme);
        localStorage.setItem("drishti_theme", theme);

        // 1. Update HTML & Body Attributes & Class
        document.documentElement.setAttribute("data-theme", theme);
        document.body.setAttribute("data-theme", theme);

        if (theme === "light") {
            document.documentElement.classList.add("theme-light");
            document.body.classList.add("theme-light");
        } else {
            document.documentElement.classList.remove("theme-light");
            document.body.classList.remove("theme-light");
        }

        // 2. Manage Dynamic Overrides for Light Mode & Dark Mode
        this.applyDynamicStyleOverrides(theme);

        // 3. Update Theme Toggle Button UI
        this.updateThemeIcon(theme);

        // 4. Synchronize GIS Leaflet Map Tiles
        this.updateMapTheme(theme);

        // 5. Synchronize Chart.js Colors
        this.updateChartsTheme(theme);

        // 6. Optional Toast Notification
        if (notify && window.alertsManager) {
            alertsManager.showToast(
                "Theme Mode Updated",
                `Interface switched to ${theme.toUpperCase()} mode.`,
                "INFO",
                2500
            );
        }
    }

    toggleTheme() {
        const nextTheme = this.currentTheme === "light" ? "dark" : "light";
        this.setTheme(nextTheme, true);
    }

    updateThemeIcon(theme) {
        const sunIcon = document.getElementById("theme-icon-sun");
        const moonIcon = document.getElementById("theme-icon-moon");
        const themeText = document.getElementById("theme-text");
        const themeBtn = document.getElementById("btn-toggle-theme");

        const isLight = theme === "light";

        if (sunIcon) sunIcon.classList.toggle("hidden", !isLight);
        if (moonIcon) moonIcon.classList.toggle("hidden", isLight);
        if (themeText) themeText.textContent = isLight ? "LIGHT" : "DARK";

        if (themeBtn) {
            const nextModeTitle = isLight ? "Switch to dark mode" : "Switch to light mode";
            themeBtn.setAttribute("title", nextModeTitle);
            themeBtn.setAttribute("aria-label", nextModeTitle);
        }

        if (window.lucide) {
            lucide.createIcons();
        }
    }

    updateMapTheme(theme) {
        if (!window.mapController) return;

        const targetMapTheme = theme === "light" ? "carto-voyager" : "carto-dark";
        mapController.setMapTheme(targetMapTheme);

        const freeMapSelect = document.getElementById("free-map-theme-select");
        if (freeMapSelect) {
            freeMapSelect.value = targetMapTheme;
        }
    }

    updateChartsTheme(theme) {
        if (window.analyticsCharts && typeof analyticsCharts.updateTheme === "function") {
            analyticsCharts.updateTheme(theme);
        }
    }

    applyDynamicStyleOverrides(theme) {
        let styleEl = document.getElementById("drishti-theme-override");

        if (!styleEl) {
            styleEl = document.createElement("style");
            styleEl.id = "drishti-theme-override";
            document.head.appendChild(styleEl);
        }

        if (theme === "light") {
            styleEl.textContent = `
                /* High-Priority Operational Brand Light Theme (#062B4A Navy Header/Sidebar, #FFFFFF Cards, #13752F Green Buttons) */
                html.theme-light, html.theme-light body, html.theme-light main {
                    background-color: #F7F6F1 !important;
                    color: #062B4A !important;
                }

                html.theme-light header {
                    background-color: #041F36 !important;
                    border-color: #0E446D !important;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
                }

                html.theme-light aside {
                    background-color: #041F36 !important;
                    border-color: #0E446D !important;
                }

                /* Panels, Cards & Stat Boxes on Light Surface */
                html.theme-light .op-panel,
                html.theme-light .op-card,
                html.theme-light .op-stat-box,
                html.theme-light .factor-chip {
                    background-color: #FFFFFF !important;
                    border-color: #CBD3D8 !important;
                    color: #062B4A !important;
                    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06) !important;
                }

                html.theme-light .op-panel-header {
                    background-color: #F0F4F7 !important;
                    border-color: #CBD3D8 !important;
                    color: #062B4A !important;
                }

                /* Light Mode: Primary Headings & Values on White Panels */
                html.theme-light .op-panel h1, 
                html.theme-light .op-panel h2, 
                html.theme-light .op-panel h3, 
                html.theme-light .op-panel h4, 
                html.theme-light .op-panel h5, 
                html.theme-light .op-panel h6,
                html.theme-light .op-panel .text-\[\#F7F6F1\],
                html.theme-light .op-card .text-\[\#F7F6F1\],
                html.theme-light .op-stat-box .text-\[\#F7F6F1\],
                html.theme-light .op-panel .text-white,
                html.theme-light .op-card .text-white,
                html.theme-light #pred-resolved-plate,
                html.theme-light #pred-last-node,
                html.theme-light #pred-raw-ocr,
                html.theme-light #pred-norm-ocr,
                html.theme-light #kpi-total-detections,
                html.theme-light #kpi-active-cameras {
                    color: #062B4A !important; /* Deep Navy Text on White Cards */
                }

                /* Light Mode: Secondary Labels, Subtitles & Grey Text on White Panels */
                html.theme-light .op-panel .text-\[\#A1B3C4\],
                html.theme-light .op-panel .text-\[\#CBD3D8\],
                html.theme-light .op-card .text-\[\#A1B3C4\],
                html.theme-light .op-card .text-\[\#CBD3D8\],
                html.theme-light .op-stat-box .text-\[\#A1B3C4\],
                html.theme-light .op-stat-box .text-\[\#CBD3D8\],
                html.theme-light .text-slate-400,
                html.theme-light .text-slate-300,
                html.theme-light .text-slate-500,
                html.theme-light .text-gray-400,
                html.theme-light .text-gray-500 {
                    color: #1E293B !important; /* Dark Charcoal Slate - 100% Crisp & Visible on White Cards */
                }

                /* Dark Navy Container Exceptions (Header, Sidebar, CCTV Tiles, Live Ticker Cards, Trajectory Timeline Cards) */
                header, aside, .cctv-tile, #live-detection-ticker .op-card, #trajectory-timeline .bg-\[\#062B4A\], #trajectory-timeline .bg-\[\#0A3655\] {
                    background-color: #041F36 !important;
                    color: #F7F6F1 !important;
                }

                #trajectory-timeline .bg-\[\#062B4A\] *,
                #trajectory-timeline .bg-\[\#0A3655\] * {
                    color: #F7F6F1 !important;
                }
                #trajectory-timeline .text-\[\#A1B3C4\],
                #trajectory-timeline .text-\[\#2E9147\] {
                    color: #CBD3D8 !important;
                }

                header .text-\[\#A1B3C4\],
                aside .text-\[\#A1B3C4\],
                .cctv-tile .text-\[\#A1B3C4\],
                .cctv-tile-header .text-\[\#A1B3C4\],
                .cctv-tile-footer .text-\[\#A1B3C4\],
                #live-detection-ticker .text-\[\#A1B3C4\],
                #live-detection-ticker .card-time-val,
                .cctv-tile .text-slate-400,
                #live-detection-ticker .text-slate-400 {
                    color: #CBD3D8 !important; /* Bright Silver-Grey on Dark Navy */
                }

                header .text-\[\#F7F6F1\],
                aside .text-\[\#F7F6F1\],
                .cctv-tile .text-\[\#F7F6F1\],
                #live-detection-ticker .text-\[\#F7F6F1\] {
                    color: #F7F6F1 !important; /* Crisp White on Dark Navy */
                }

                .bg-\[\#0A3655\],
                .bg-\[\#0A3655\] .text-\[\#A1B3C4\],
                .bg-\[\#0A3655\] button,
                html.theme-light .bg-\[\#0A3655\] .text-\[\#A1B3C4\],
                html.theme-light .bg-\[\#0A3655\] button {
                    color: #CBD3D8 !important;
                }

                /* Form Controls & Inputs in Light Mode */
                html.theme-light .op-input,
                html.theme-light select,
                html.theme-light input {
                    background-color: #FFFFFF !important;
                    border-color: #CBD3D8 !important;
                    color: #062B4A !important;
                }

                /* Table Styling in Light Mode */
                html.theme-light .op-table th {
                    background-color: #F0F4F7 !important;
                    color: #062B4A !important;
                    border-color: #CBD3D8 !important;
                }
                html.theme-light .op-table td {
                    background-color: #FFFFFF !important;
                    border-color: #EEF1F2 !important;
                    color: #062B4A !important;
                }
                html.theme-light .op-table tr:hover td {
                    background-color: #F7F6F1 !important;
                }

                /* Header and Sidebar Text Exemptions (Header & Sidebar remain dark navy background) */
                header, aside {
                    background-color: #041F36 !important;
                }
                header .text-\[\#A1B3C4\] { color: #A1B3C4 !important; }
                header .text-\[\#F7F6F1\] { color: #F7F6F1 !important; }
                aside .text-\[\#A1B3C4\] { color: #A1B3C4 !important; }
                aside .text-\[\#F7F6F1\] { color: #F7F6F1 !important; }

                /* Form Controls & Inputs */
                html.theme-light .op-input,
                html.theme-light select,
                html.theme-light input {
                    background-color: #FFFFFF !important;
                    border-color: #CBD3D8 !important;
                    color: #062B4A !important;
                }

                /* Table Styling */
                html.theme-light .op-table th {
                    background-color: #F0F4F7 !important;
                    color: #062B4A !important;
                    border-color: #CBD3D8 !important;
                }
                html.theme-light .op-table td {
                    background-color: #FFFFFF !important;
                    border-color: #EEF1F2 !important;
                    color: #062B4A !important;
                }
                html.theme-light .op-table tr:hover td {
                    background-color: #F7F6F1 !important;
                }
            `;
        } else {
            styleEl.textContent = `
                /* High-Priority Operational Brand Dark Theme (#031D33 Navy Canvas, #041F36 Header/Sidebar, #062B4A Cards, #13752F Green Actions) */
                html, body, main {
                    background-color: #031D33 !important;
                    color: #F7F6F1 !important;
                }

                header, aside {
                    background-color: #041F36 !important;
                    border-color: #0E446D !important;
                }
            `;
        }
    }
}

const themeController = new ThemeController();
window.themeController = themeController;
