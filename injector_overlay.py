"""
injector_overlay.py - 9kCLUB HACK VIP Injector Overlay
Injects the 9kCLUB Cyber Core HACK widget directly on top of the WinGo winning popup
for screenshots sent to users / Telegram channels.
"""

import os
import json
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHIPS_FILE = os.path.join(BASE_DIR, "injector_chips.json")

# Load base64 chip URIs
CHIPS = {}
if os.path.exists(CHIPS_FILE):
    try:
        with open(CHIPS_FILE, "r", encoding="utf-8") as f:
            CHIPS = json.load(f)
    except Exception as e:
        print(f"[injector_overlay] Failed to load chips: {e}")

# Base CSS from 9kvip.html
CSS_STYLE = """
:root {
  --neon-red: #ff003c;
  --neon-glow: rgba(255, 0, 60, 0.45);
  --neon-gold: #ffd000;
  --neon-green: #00ff88;
  --neon-violet: #9d4edd;
  --bg-deep: #070104;
  --bg-card: #0d0208;
  --bg-screen: #0a0206;
  --card-w: 224px;
  --f-sans: 'Montserrat', system-ui, -apple-system, sans-serif;
  --f-mono: 'JetBrains Mono', monospace;
}

#miniBtn {
  position: fixed !important;
  top: 18px !important;
  right: 15px !important;
  width: 50px !important;
  height: 50px !important;
  border-radius: 50% !important;
  background: radial-gradient(circle at 35% 30%, #ff1a53 0%, #a00024 55%, #40000e 100%) !important;
  border: 1.5px solid #ff4d79 !important;
  box-shadow: 0 0 16px rgba(255, 0, 60, 0.65), inset 0 2px 4px rgba(255, 255, 255, 0.5), inset 0 -3px 6px rgba(0, 0, 0, 0.85) !important;
  z-index: 2147483647 !important;
  cursor: pointer !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-sizing: border-box !important;
}

.mb-ring {
  position: absolute;
  inset: -3px;
  width: calc(100% + 6px);
  height: calc(100% + 6px);
  pointer-events: none;
  animation: coinSpinRing 7s linear infinite;
}
.mb-ring circle.r1 {
  fill: none;
  stroke: #ffd000;
  stroke-width: 1;
  stroke-dasharray: 4, 3;
}
.mb-ring circle.r2 {
  fill: none;
  stroke: #ff003c;
  stroke-width: 0.8;
  stroke-dasharray: 8, 4;
}
@keyframes coinSpinRing {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.mb-center-bolt {
  position: relative;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bolt-svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 0 5px rgba(255, 208, 0, 0.9));
}

.mb-counter-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  background: #ffd000;
  color: #000;
  font-size: 8px;
  font-weight: 900;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 5px rgba(255, 208, 0, 0.8);
  font-family: sans-serif;
}

#injector-container {
  position: fixed !important;
  top: 36px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  z-index: 2147483647 !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: auto !important;
  font-family: var(--f-sans);
  box-sizing: border-box !important;
}

.card-outer {
  position: relative;
  width: var(--card-w);
  background: radial-gradient(circle at 50% 0%, #1e030a 0%, #0d0206 50%, #060103 100%);
  border-radius: 16px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.95), 0 0 25px rgba(255, 0, 60, 0.4), inset 0 0 15px rgba(255, 0, 60, 0.18);
  border: 1.2px solid rgba(255, 0, 60, 0.7);
  box-sizing: border-box;
}

.card-stroke {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 8;
  display: block !important;
  overflow: visible;
}
.card-stroke rect {
  fill: none;
  stroke: #ffd166;
  stroke-width: 1.8;
  stroke-dasharray: 22 78;
  stroke-dashoffset: 0;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
  animation: runningStroke 3.4s linear infinite;
  filter: drop-shadow(0 0 4px rgba(255, 164, 0, 0.95)) drop-shadow(0 0 10px rgba(255, 74, 0, 0.55));
}
@keyframes runningStroke {
  from { stroke-dashoffset: 100; }
  to { stroke-dashoffset: 0; }
}

.card-title-line1 {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(180deg, #ff3b6d 0%, #d00035 56%, #78001b 100%);
  border: 1px solid #ff8aa5;
  border-radius: 14px;
  padding: 2px 10px;
  font-size: 7.6px;
  font-weight: 900;
  letter-spacing: 0.12em;
  color: #ffffff;
  text-transform: uppercase;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.7), 0 0 10px rgba(255, 0, 60, 0.7), inset 0 1px 1px rgba(255, 255, 255, 0.5);
  z-index: 10;
}

.card-bracket {
  position: absolute;
  width: 9px;
  height: 9px;
  pointer-events: none;
  z-index: 6;
}
.card-bracket::before, .card-bracket::after {
  content: '';
  position: absolute;
  background: #ff003c;
  box-shadow: 0 0 5px #ff003c;
}
.b-tl { top: -2px; left: -2px; }
.b-tl::before { top: 0; left: 0; width: 7px; height: 1.5px; }
.b-tl::after  { top: 0; left: 0; width: 1.5px; height: 7px; }
.b-tr { top: -2px; right: -2px; }
.b-tr::before { top: 0; right: 0; width: 7px; height: 1.5px; }
.b-tr::after  { top: 0; right: 0; width: 1.5px; height: 7px; }
.b-bl { bottom: -2px; left: -2px; }
.b-bl::before { bottom: 0; left: 0; width: 7px; height: 1.5px; }
.b-bl::after  { bottom: 0; left: 0; width: 1.5px; height: 7px; }
.b-br { bottom: -2px; right: -2px; }
.b-br::before { bottom: 0; right: 0; width: 7px; height: 1.5px; }
.b-br::after  { bottom: 0; right: 0; width: 1.5px; height: 7px; }

.card-inner {
  position: relative;
  padding: 7px 6px 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 2;
}

.card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}
.mode-strip {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(15, 2, 8, 0.85);
  border: 1px solid rgba(255, 0, 60, 0.4);
  border-radius: 6px;
  padding: 2.5px 5px;
  font-family: monospace;
  font-size: 6.2px;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: #ffffff;
  box-sizing: border-box;
}
.strip-item {
  display: flex;
  align-items: center;
  gap: 2px;
}
.strip-item span:first-child {
  color: rgba(255, 255, 255, 0.75);
}
.strip-val {
  color: #ffffff;
  font-weight: 900;
}

.card-screen {
  position: relative;
  width: 100%;
  min-height: 118px;
  background: #080105;
  border-radius: 9px;
  border: 1px solid rgba(255, 0, 60, 0.35);
  overflow: hidden;
  padding: 6px 5px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.screen-cyber-matrix {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}
.circuit-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.25;
}
.telemetry-hud-tag {
  position: absolute;
  font-family: monospace;
  font-size: 5.6px;
  font-weight: 800;
  color: rgba(255, 208, 0, 0.8);
  letter-spacing: 0.05em;
}
.tele-tag-tl { top: 3px; left: 4px; }
.tele-tag-tr { top: 3px; right: 4px; }
.tele-tag-bl { bottom: 3px; left: 4px; color: rgba(0, 255, 136, 0.8); }
.tele-tag-br { bottom: 3px; right: 4px; color: rgba(255, 0, 60, 0.8); }

.sc-corner {
  position: absolute;
  width: 6px;
  height: 6px;
  pointer-events: none;
  z-index: 2;
}
.sc-corner::before, .sc-corner::after {
  content: '';
  position: absolute;
  background: rgba(255, 208, 0, 0.75);
}
.sc-tl { top: 2px; left: 2px; }
.sc-tl::before { top: 0; left: 0; width: 4px; height: 1px; }
.sc-tl::after  { top: 0; left: 0; width: 1px; height: 4px; }
.sc-tr { top: 2px; right: 2px; }
.sc-tr::before { top: 0; right: 0; width: 4px; height: 1px; }
.sc-tr::after  { top: 0; right: 0; width: 1px; height: 4px; }
.sc-bl { bottom: 2px; left: 2px; }
.sc-bl::before { bottom: 0; left: 0; width: 4px; height: 1px; }
.sc-bl::after  { bottom: 0; left: 0; width: 1px; height: 4px; }
.sc-br { bottom: 2px; right: 2px; }
.sc-br::before { bottom: 0; right: 0; width: 4px; height: 1px; }
.sc-br::after  { bottom: 0; right: 0; width: 1px; height: 4px; }

#sv-result {
  position: relative;
  z-index: 3;
  width: 100%;
  display: flex !important;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.pred-showcase-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 2px;
  box-sizing: border-box;
}

.res-outcome-ingot {
  position: relative;
  width: 98px;
  height: 48px;
  border-radius: 9px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.7), inset 0 1px 2px rgba(255, 255, 255, 0.4), inset 0 -2px 4px rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-sizing: border-box;
}
.res-outcome-ingot.big {
  background: linear-gradient(180deg, #ff1a53 0%, #c4002c 50%, #750017 100%);
  border-color: #ff5c85;
  box-shadow: 0 4px 14px rgba(255, 0, 60, 0.45), inset 0 1px 2px rgba(255, 255, 255, 0.5);
}
.res-outcome-ingot.small {
  background: linear-gradient(180deg, #00d2ff 0%, #0077b6 50%, #023e8a 100%);
  border-color: #48cae4;
  box-shadow: 0 4px 14px rgba(0, 180, 216, 0.45), inset 0 1px 2px rgba(255, 255, 255, 0.5);
}

.ingot-top-tag {
  font-size: 6px;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.9);
  text-transform: uppercase;
}
.ingot-main-text {
  font-size: 21px;
  font-weight: 900;
  letter-spacing: 0.08em;
  color: #ffffff;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.7), 0 0 12px rgba(255, 255, 255, 0.8);
  line-height: 1;
  margin: 1px 0;
}
.ingot-conf-pill {
  display: flex;
  align-items: center;
  gap: 3px;
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  padding: 1px 6px;
  font-family: monospace;
  font-size: 6px;
  font-weight: 900;
  color: #ffd000;
}
.conf-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #00ff88;
  box-shadow: 0 0 4px #00ff88;
}

.res-chip-pedestal {
  position: relative;
  width: 90px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.pedestal-radar-rings {
  position: absolute;
  top: 18px;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 44px;
  height: 44px;
  pointer-events: none;
}
.ped-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1px dashed rgba(255, 208, 0, 0.4);
}
.ped-ring.ring-inner {
  inset: 5px;
  border-color: rgba(255, 0, 60, 0.5);
  border-style: dotted;
}

.ball-ambient-glow {
  position: absolute;
  top: 18px;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 48px;
  height: 48px;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(4px);
}

.res-ball {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.8);
}
.ball-bg-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}
.res-num-text {
  position: relative;
  z-index: 2;
  font-size: 16px;
  font-weight: 900;
  color: #ffffff;
  text-shadow: 0 1px 4px #000, 0 0 8px rgba(255, 255, 255, 0.9);
}

.res-color-pill {
  margin-top: 3px;
  background: rgba(10, 2, 6, 0.85);
  border: 1px solid rgba(255, 0, 60, 0.5);
  border-radius: 6px;
  padding: 1.5px 5px;
  font-family: monospace;
  font-size: 6.2px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.api-id-horizon {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 1px;
  font-family: monospace;
  font-size: 6px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.85);
}
.horizon-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(255, 0, 60, 0.6) 50%, transparent 100%);
}
.horizon-acc {
  color: #00ff88;
  font-weight: 900;
}

.hist-balls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 1px 4px 0;
  box-sizing: border-box;
}
.h-chip-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}
.h-mini-chip {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background-size: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.6);
}
.h-mini-num {
  font-size: 7.5px;
  font-weight: 900;
  color: #fff;
  text-shadow: 0 1px 2px #000;
}
.h-pip {
  font-size: 5.5px;
  font-weight: 900;
  border-radius: 2px;
  padding: 0 2px;
  line-height: 1.2;
}
.h-pip.b { background: #ff003c; color: #fff; }
.h-pip.s { background: #0077b6; color: #fff; }

.card-buttons {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 5px;
  width: 100%;
  margin-top: 1px;
}
#action-btn {
  flex: 1;
  background: linear-gradient(180deg, #ff1a53 0%, #c4002c 50%, #750017 100%);
  border: 1px solid #ff4d79;
  border-radius: 7px;
  color: #ffffff;
  font-family: var(--f-sans);
  font-size: 7.5px;
  font-weight: 900;
  letter-spacing: 0.1em;
  padding: 4px 0;
  text-align: center;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.6), inset 0 1px 1px rgba(255, 255, 255, 0.4);
}
.hide-btn {
  background: rgba(20, 3, 10, 0.85);
  border: 1px solid rgba(255, 0, 60, 0.4);
  border-radius: 7px;
  color: rgba(255, 255, 255, 0.8);
  font-family: var(--f-sans);
  font-size: 7px;
  font-weight: 800;
  padding: 4px 7px;
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
}
"""

def inject_9kvip_overlay(page, period=None, win_num=None, outcome=None, conf=None):
    """
    Injects the 9kCLUB HACK VIP overlay into the current Playwright page DOM
    so that it appears directly over the winning popup before screenshot capture.
    """
    try:
        # Determine winning number & outcome if not explicitly passed
        # Default fallback: 7 (BIG, GREEN)
        target_num = 7
        target_outcome = "BIG"
        target_conf = conf or f"{round(random.uniform(98.8, 99.7), 1)}%"
        target_period = str(period)[-5:] if period else "10328"

        if win_num is not None:
            try:
                target_num = int(win_num)
            except Exception:
                target_num = 7
        
        if outcome:
            target_outcome = outcome.upper()
        else:
            target_outcome = "BIG" if target_num >= 5 else "SMALL"

        # Determine color label, glow, and chip URI
        if target_num == 0:
            label = "RED + VIOLET"
            glow = "radial-gradient(circle, rgba(157, 78, 221, 0.75) 0%, rgba(255, 0, 60, 0.5) 50%, transparent 75%)"
            chip_uri = CHIPS.get("CHIP_0_RED_VIOLET_URI", "")
        elif target_num == 5:
            label = "GREEN + VIOLET"
            glow = "radial-gradient(circle, rgba(157, 78, 221, 0.75) 0%, rgba(0, 255, 136, 0.5) 50%, transparent 75%)"
            chip_uri = CHIPS.get("CHIP_5_GREEN_VIOLET_URI", "")
        elif target_num % 2 == 0:
            label = "RED"
            glow = "radial-gradient(circle, rgba(255, 0, 60, 0.7) 0%, transparent 70%)"
            chip_uri = CHIPS.get("CHIP_RED_URI", "")
        else:
            label = "GREEN"
            glow = "radial-gradient(circle, rgba(0, 255, 136, 0.7) 0%, transparent 70%)"
            chip_uri = CHIPS.get("CHIP_GREEN_URI", "")

        is_big = (target_outcome == "BIG")

        # History chips fallback
        chip_red = CHIPS.get("CHIP_RED_URI", "")
        chip_green = CHIPS.get("CHIP_GREEN_URI", "")

        payload = {
            "period": target_period,
            "num": target_num,
            "outcome": target_outcome,
            "is_big": is_big,
            "conf": target_conf,
            "label": label,
            "glow": glow,
            "chip_uri": chip_uri,
            "chip_red": chip_red,
            "chip_green": chip_green,
            "css": CSS_STYLE
        }

        # Evaluate JS injection inside page
        result = page.evaluate("""(data) => {
            try {
                // 1. Remove any previous injector
                const oldContainer = document.getElementById('injector-container');
                if (oldContainer) oldContainer.remove();
                const oldBtn = document.getElementById('miniBtn');
                if (oldBtn) oldBtn.remove();
                const oldStyle = document.getElementById('injector-custom-style');
                if (oldStyle) oldStyle.remove();

                // 2. Inject CSS
                const styleEl = document.createElement('style');
                styleEl.id = 'injector-custom-style';
                styleEl.innerHTML = data.css;
                document.head.appendChild(styleEl);

                // 3. Inject Floating Coin (#miniBtn)
                const miniBtn = document.createElement('div');
                miniBtn.id = 'miniBtn';
                miniBtn.innerHTML = `
                    <svg class="mb-ring" viewBox="0 0 60 60">
                        <circle class="r1" cx="30" cy="30" r="28"/>
                        <circle class="r2" cx="30" cy="30" r="26"/>
                    </svg>
                    <div class="mb-center-bolt">
                        <svg class="bolt-svg" viewBox="0 0 24 24" fill="none">
                            <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" fill="#ffd000" stroke="#ff003c" stroke-width="1.2" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="mb-counter-badge">9K</div>
                `;
                document.body.appendChild(miniBtn);

                // 4. Inject Main Card (#injector-container)
                const ingotClass = data.is_big ? 'res-outcome-ingot big' : 'res-outcome-ingot small';

                const container = document.createElement('div');
                container.id = 'injector-container';
                container.innerHTML = `
                    <div id="cardOuter" class="card-outer">
                        <!-- SINGLE GOLD LASER RUNNING STROKE -->
                        <svg class="card-stroke" viewBox="0 0 216 203" preserveAspectRatio="none" aria-hidden="true">
                            <rect x="1" y="1" width="214" height="201" pathLength="100" rx="16"/>
                        </svg>

                        <!-- TOP DOCKED PILL BADGE -->
                        <div class="card-title-line1">9kCLUB HACK</div>

                        <!-- 4 CORNER NOTCH BRACKETS -->
                        <div class="card-bracket b-tl"></div>
                        <div class="card-bracket b-tr"></div>
                        <div class="card-bracket b-bl"></div>
                        <div class="card-bracket b-br"></div>

                        <div class="card-inner">
                            <!-- STATUS STRIP -->
                            <div class="card-header">
                                <div class="mode-strip">
                                    <div class="strip-item">
                                        <span>SYS : </span><span class="strip-val">SECURE PRO</span>
                                    </div>
                                    <div class="strip-item">
                                        <span>MOD : </span><span id="modeBadge">READY</span>
                                    </div>
                                    <div class="strip-item">
                                        <span>PING : </span><span id="stat-ping">21MS</span>
                                    </div>
                                </div>
                            </div>

                            <!-- INNER SCREEN VIEWPORT -->
                            <div class="card-screen" id="cardScreen">
                                <!-- Cyber Circuit Matrix -->
                                <div class="screen-cyber-matrix">
                                    <svg class="circuit-svg" viewBox="0 0 240 120" preserveAspectRatio="none">
                                        <path d="M 0 20 L 35 20 L 48 35 L 95 35 M 145 35 L 192 35 L 205 20 L 240 20" stroke="#ff003c" stroke-width="0.8" fill="none"/>
                                        <path d="M 0 100 L 40 100 L 52 85 L 90 85 M 150 85 L 188 85 L 200 100 L 240 100" stroke="#ff003c" stroke-width="0.8" fill="none"/>
                                        <circle cx="48" cy="35" r="1.5" fill="#ffd000"/>
                                        <circle cx="192" cy="35" r="1.5" fill="#ffd000"/>
                                        <circle cx="52" cy="85" r="1.5" fill="#00ff88"/>
                                        <circle cx="188" cy="85" r="1.5" fill="#00ff88"/>
                                    </svg>
                                    <div class="telemetry-hud-tag tele-tag-tl">◈ 0x9K-AI</div>
                                    <div class="telemetry-hud-tag tele-tag-tr">SYNC: 99.8% ◈</div>
                                    <div class="telemetry-hud-tag tele-tag-bl">⌖ MATRIX: ON</div>
                                    <div class="telemetry-hud-tag tele-tag-br">5.8GHz ⌖</div>
                                </div>

                                <div class="sc-corner sc-tl"></div>
                                <div class="sc-corner sc-tr"></div>
                                <div class="sc-corner sc-bl"></div>
                                <div class="sc-corner sc-br"></div>

                                <!-- PREDICTION RESULT -->
                                <div id="sv-result">
                                    <!-- Top Row: Ingot + Ball Pedestal -->
                                    <div class="pred-showcase-row">
                                        <!-- Ingot -->
                                        <div class="${ingotClass}" id="resBsBadge">
                                            <div class="ingot-top-tag">★ AI VERDICT ★</div>
                                            <div class="ingot-main-text" id="resBsText">${data.outcome}</div>
                                            <div class="ingot-conf-pill">
                                                <span class="conf-dot"></span>
                                                <span id="resConfText">CONF: ${data.conf}</span>
                                            </div>
                                        </div>

                                        <!-- Right: Chip Pedestal -->
                                        <div class="res-chip-pedestal" id="podiumLeft">
                                            <div class="pedestal-radar-rings">
                                                <div class="ped-ring ring-outer"></div>
                                                <div class="ped-ring ring-inner"></div>
                                            </div>
                                            <div class="ball-ambient-glow" id="ballAmbientGlow" style="background:${data.glow};"></div>
                                            <div class="res-ball" id="resBall">
                                                <img class="ball-bg-img" id="ballBgImg" src="${data.chip_uri}" alt="Ball">
                                                <span class="res-num-text" id="resNumText">${data.num}</span>
                                            </div>
                                            <div class="res-color-pill" id="resColorPill">COLOR: ${data.label}</div>
                                        </div>
                                    </div>

                                    <!-- Middle: Horizon Period -->
                                    <div class="api-id-horizon">
                                        <span class="horizon-line"></span>
                                        <span id="res-period-bottom">API ID : ${data.period}</span>
                                        <span class="horizon-acc">99.8% ACC</span>
                                        <span class="horizon-line"></span>
                                    </div>

                                    <!-- Bottom: Mini Historical Row -->
                                    <div class="hist-balls-row" id="histBallsRow">
                                        <div class="h-chip-col"><div class="h-mini-chip" style="background-image:url('${data.chip_red}');"><span class="h-mini-num">8</span></div><span class="h-pip b">B</span></div>
                                        <div class="h-chip-col"><div class="h-mini-chip" style="background-image:url('${data.chip_red}');"><span class="h-mini-num">2</span></div><span class="h-pip s">S</span></div>
                                        <div class="h-chip-col"><div class="h-mini-chip" style="background-image:url('${data.chip_green}');"><span class="h-mini-num">5</span></div><span class="h-pip b">B</span></div>
                                        <div class="h-chip-col"><div class="h-mini-chip" style="background-image:url('${data.chip_red}');"><span class="h-mini-num">0</span></div><span class="h-pip s">S</span></div>
                                        <div class="h-chip-col"><div class="h-mini-chip" style="background-image:url('${data.chip_green}');"><span class="h-mini-num">7</span></div><span class="h-pip b">B</span></div>
                                        <div class="h-chip-col"><div class="h-mini-chip" style="background-image:url('${data.chip_red}');"><span class="h-mini-num">4</span></div><span class="h-pip s">S</span></div>
                                    </div>
                                </div>
                            </div>

                            <!-- BUTTONS -->
                            <div class="card-buttons">
                                <button id="action-btn" type="button">HACK ACTIVE</button>
                                <button class="hide-btn" type="button">
                                    <svg viewBox="0 0 24 24" width="11" height="11" fill="none">
                                        <path d="M1 12S5 5 12 5S23 12 23 12S19 19 12 19S1 12 1 12Z" stroke="#ff3366" stroke-width="2"/>
                                        <circle cx="12" cy="12" r="3" fill="#ff003c"/>
                                    </svg>
                                    <span>LIVE</span>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(container);
                return { success: true };
            } catch (err) {
                return { success: false, error: String(err) };
            }
        }""", payload)
        return result
    except Exception as e:
        print(f"[injector_overlay] Error injecting overlay: {e}")
        return {"success": False, "error": str(e)}
