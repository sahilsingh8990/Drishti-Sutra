// Alerts and Audio Management
class AlertsManager {
    constructor() {
        this.soundEnabled = true;
        this.audioCtx = null;
    }

    initAudio() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioCtx = new AudioContext();
        }
    }

    playAlertTone(type = "critical") {
        if (!this.soundEnabled) return;
        try {
            this.initAudio();
            if (this.audioCtx.state === 'suspended') {
                this.audioCtx.resume();
            }

            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);

            const now = this.audioCtx.currentTime;

            if (type === "critical") {
                // High alert two-tone ping
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(880, now);
                osc.frequency.setValueAtTime(1100, now + 0.12);
                gain.gain.setValueAtTime(0.2, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
                osc.start(now);
                osc.stop(now + 0.45);
            } else {
                // Gentle detection radar ping
                osc.type = "sine";
                osc.frequency.setValueAtTime(587.33, now); // D5
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.1); // A5
                gain.gain.setValueAtTime(0.08, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
                osc.start(now);
                osc.stop(now + 0.25);
            }
        } catch (e) {
            console.warn("Audio playback not allowed until user interaction", e);
        }
    }

    showToast(title, message, severity = "INFO", duration = 6000) {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `p-4 rounded-xl shadow-2xl border transition-all duration-300 transform translate-y-2 flex items-start space-x-3 pointer-events-auto ${
            severity === "CRITICAL"
                ? "bg-red-950/90 border-red-500/50 text-red-100"
                : severity === "HIGH"
                ? "bg-amber-950/90 border-amber-500/50 text-amber-100"
                : "bg-slate-900/90 border-cyan-500/40 text-cyan-100"
        }`;

        const iconHtml = severity === "CRITICAL"
            ? `<div class="p-2 rounded-lg bg-red-500/20 text-red-400"><i data-lucide="shield-alert" class="w-5 h-5"></i></div>`
            : `<div class="p-2 rounded-lg bg-cyan-500/20 text-cyan-400"><i data-lucide="bell" class="w-5 h-5"></i></div>`;

        toast.innerHTML = `
            ${iconHtml}
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                    <h4 class="font-bold text-sm truncate">${title}</h4>
                    <span class="text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold ${
                        severity === "CRITICAL" ? "bg-red-500/30 text-red-300" : "bg-cyan-500/30 text-cyan-300"
                    }">${severity}</span>
                </div>
                <p class="text-xs mt-1 text-slate-300 leading-relaxed">${message}</p>
            </div>
            <button class="text-slate-400 hover:text-white" onclick="this.parentElement.remove()">
                <i data-lucide="x" class="w-4 h-4"></i>
            </button>
        `;

        container.appendChild(toast);
        if (window.lucide) lucide.createIcons();

        if (severity === "CRITICAL") {
            this.playAlertTone("critical");
        }

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(-10px)";
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

const alertsManager = new AlertsManager();
