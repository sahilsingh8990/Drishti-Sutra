// ============================================================
// DRISHTI-SUTRA INTEGRATED TRAFFIC COMMAND CENTRE (ICCC)
// Centralized Theme Controller (Dark <-> Light White/Black)
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

        // 2. Manage Dynamic Overrides for Light Mode (White/Black Contrast)
        this.applyDynamicStyleOverrides(theme);

        // 3. Update Theme Toggle Button UI (Icon, Text, Accessibility)
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

        if (theme === "light") {
            if (!styleEl) {
                styleEl = document.createElement("style");
                styleEl.id = "drishti-theme-override";
                document.head.appendChild(styleEl);
            }

            styleEl.textContent = `
                /* High-Priority Operational Light Theme (Pure White & Black Contrast) */
                html.theme-light, html.theme-light body, html.theme-light main {
                    background-color: #f4f6f9 !important;
                    color: #0f172a !important;
                }

                html.theme-light header {
                    background-color: #ffffff !important;
                    border-color: #cbd5e1 !important;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
                }

                html.theme-light aside {
                    background-color: #ffffff !important;
                    border-color: #cbd5e1 !important;
                }

                /* Operational Panels, Cards, Stat Boxes & Factor Chips */
                html.theme-light .op-panel,
                html.theme-light .op-card,
                html.theme-light .op-stat-box,
                html.theme-light .factor-chip {
                    background-color: #ffffff !important;
                    border-color: #cbd5e1 !important;
                    color: #0f172a !important;
                    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05) !important;
                }

                html.theme-light .op-panel-header {
                    background-color: #f1f5f9 !important;
                    border-color: #e2e8f0 !important;
                    color: #0f172a !important;
                }

                /* Card Containers & Grid Elements */
                html.theme-light div.bg-slate-900,
                html.theme-light div.bg-slate-950,
                html.theme-light div.bg-slate-800,
                html.theme-light div.bg-slate-800\\/80,
                html.theme-light div.bg-slate-800\\/60,
                html.theme-light div.bg-slate-900\\/80,
                html.theme-light div.bg-slate-900\\/90,
                html.theme-light div.bg-sky-950,
                html.theme-light div.bg-purple-950,
                html.theme-light div.bg-cyan-950 {
                    background-color: #ffffff !important;
                    border-color: #cbd5e1 !important;
                    color: #0f172a !important;
                }

                /* Typography Text Overrides */
                html.theme-light h1, html.theme-light h2, html.theme-light h3, html.theme-light h4, html.theme-light h5, html.theme-light h6 {
                    color: #0f172a !important;
                }

                html.theme-light .text-slate-100,
                html.theme-light .text-slate-200,
                html.theme-light .text-slate-300,
                html.theme-light .text-white {
                    color: #0f172a !important;
                }

                html.theme-light .text-slate-400 {
                    color: #475569 !important;
                }

                html.theme-light .text-slate-500 {
                    color: #64748b !important;
                }

                /* Borders */
                html.theme-light .border-slate-800,
                html.theme-light .border-slate-900,
                html.theme-light .border-slate-700,
                html.theme-light .border-sky-800,
                html.theme-light .border-purple-800,
                html.theme-light .border-cyan-800 {
                    border-color: #cbd5e1 !important;
                }

                /* Navigation Buttons & Sidebar Tabs */
                html.theme-light .tab-btn {
                    color: #475569 !important;
                }
                html.theme-light .tab-btn:hover {
                    background-color: #f1f5f9 !important;
                    color: #0f172a !important;
                }
                html.theme-light .tab-btn.bg-sky-950\\/80,
                html.theme-light .tab-btn[class*="bg-sky-950"] {
                    background-color: #e0f2fe !important;
                    color: #0284c7 !important;
                    border-color: #0284c7 !important;
                }

                /* Form Controls, Inputs & Selects */
                html.theme-light .op-input,
                html.theme-light select,
                html.theme-light input,
                html.theme-light textarea {
                    background-color: #ffffff !important;
                    border-color: #cbd5e1 !important;
                    color: #0f172a !important;
                }

                /* Buttons */
                html.theme-light .op-btn,
                html.theme-light button:not(.op-btn-primary):not(.op-btn-purple):not(.op-btn-danger):not(.tab-btn) {
                    background-color: #ffffff !important;
                    border-color: #cbd5e1 !important;
                    color: #1e293b !important;
                }

                /* Tables */
                html.theme-light .op-table th {
                    background-color: #f1f5f9 !important;
                    color: #475569 !important;
                    border-color: #cbd5e1 !important;
                }

                html.theme-light .op-table td {
                    background-color: #ffffff !important;
                    border-color: #e2e8f0 !important;
                    color: #1e293b !important;
                }

                html.theme-light .op-table tr:hover td {
                    background-color: #f8fafc !important;
                }

                /* GIS Map Container */
                html.theme-light .leaflet-container {
                    background-color: #f1f5f9 !important;
                }
            `;
        } else {
            if (styleEl) {
                styleEl.remove();
            }
        }
    }
}

const themeController = new ThemeController();
window.themeController = themeController;
