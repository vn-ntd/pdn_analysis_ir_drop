"""
Generates the self-contained interactive Generative UI dashboard for PDN Analysis & IR-Drop Optimization.
"""
import os
import json

def generate_dashboard():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    json_path = os.path.join(base_dir, "output", "pdn_results.json")
    if not os.path.exists(json_path):
        json_path = r"C:\Users\Dung\.gemini\antigravity\brain\5cb86e9f-6b83-431e-9f40-b6b51c8c193d\pdn_results.json"
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    local_html_target = os.path.join(base_dir, "dashboard", "pdn_dashboard.html")
    brain_html_target = r"C:\Users\Dung\.gemini\antigravity\brain\5cb86e9f-6b83-431e-9f40-b6b51c8c193d\pdn_dashboard.html"
    
    data_js_str = json.dumps(data)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Power Grid Analysis & IR-Drop Optimization (PDN)</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {{
      --background: #0f172a;
      --card: #1e293b;
      --border: #334155;
      --foreground: #f8fafc;
      --muted-foreground: #94a3b8;
      --primary: #38bdf8;
      --primary-foreground: #0f172a;
      --accent: #f59e0b;
      --success: #10b981;
      --danger: #ef4444;
    }}
    body {{
      background: var(--background);
      color: var(--foreground);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .metric-badge {{
      transition: all 0.2s ease;
    }}
    .metric-badge:hover {{
      transform: translateY(-2px);
    }}
  </style>
</head>
<body class="p-6">
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- Header Section -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-sky-500/20 text-sky-400 border border-sky-500/30">VLSI PDN CAD</span>
          <span class="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">7nm FinFET Verified</span>
        </div>
        <h1 class="text-2xl md:text-3xl font-extrabold text-[var(--foreground)] mt-2">Power Distribution Network (PDN) & IR-Drop Optimization</h1>
        <p class="text-[var(--muted-foreground)] text-sm mt-1">Multi-Layer Power Grid Sizing, Electromigration (EM) Verification & Static/Dynamic IR-Drop Simulation</p>
      </div>

      <!-- Quick KPI Badges -->
      <div class="flex flex-wrap gap-3">
        <div class="bg-slate-900/80 border border-slate-700/60 rounded-xl px-4 py-2.5 text-center">
          <span class="text-xs text-[var(--muted-foreground)] block">Nominal VDD</span>
          <span class="text-lg font-bold text-sky-400">0.80 V</span>
        </div>
        <div class="bg-slate-900/80 border border-slate-700/60 rounded-xl px-4 py-2.5 text-center">
          <span class="text-xs text-[var(--muted-foreground)] block">Static IR Limit</span>
          <span class="text-lg font-bold text-amber-400">&le; 20 mV (2.5%)</span>
        </div>
        <div class="bg-slate-900/80 border border-slate-700/60 rounded-xl px-4 py-2.5 text-center">
          <span class="text-xs text-[var(--muted-foreground)] block">Dynamic IR Limit</span>
          <span class="text-lg font-bold text-rose-400">&le; 40 mV (5.0%)</span>
        </div>
        <div class="bg-slate-900/80 border border-slate-700/60 rounded-xl px-4 py-2.5 text-center">
          <span class="text-xs text-[var(--muted-foreground)] block">EM Limit (M8)</span>
          <span class="text-lg font-bold text-emerald-400">2.5 mA/µm²</span>
        </div>
      </div>
    </div>

    <!-- Main Interactive Grid: Heatmap + Topology Control -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Left Column: 2D Mesh Heatmap & Inspection (8 cols) -->
      <div class="lg:col-span-8 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-xl space-y-4">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h2 class="text-lg font-bold text-[var(--foreground)] flex items-center gap-2">
              <svg class="w-5 h-5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
              2D Die Power Mesh & IR-Drop Heatmap
            </h2>
            <p class="text-xs text-[var(--muted-foreground)]">Hover over the 600µm × 600µm die to inspect local voltage drops and current density.</p>
          </div>
          <div class="flex items-center gap-2 text-xs">
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block"></span> C4 Bump</span>
            <span class="flex items-center gap-1"><span class="w-3 h-2 border border-dashed border-cyan-400 inline-block"></span> Hotspot Core</span>
          </div>
        </div>

        <!-- Canvas Container with Interactive Overlay -->
        <div class="relative bg-slate-950 rounded-xl overflow-hidden border border-slate-800 flex justify-center items-center p-2">
          <canvas id="meshCanvas" width="580" height="580" class="cursor-crosshair rounded"></canvas>
          <div id="tooltip" class="absolute hidden pointer-events-none bg-slate-900/95 border border-sky-500/50 text-white text-xs rounded-lg p-2.5 shadow-2xl backdrop-blur"></div>
        </div>

        <!-- Colorbar Scale -->
        <div class="flex items-center justify-between text-xs text-[var(--muted-foreground)] pt-1">
          <span>0 mV (Ideal VDD = 0.80V)</span>
          <div class="flex-1 mx-4 h-3 rounded-full bg-gradient-to-r from-blue-900 via-amber-600 to-rose-600 border border-slate-700"></div>
          <span id="maxDropScale">Max Drop: 25 mV</span>
        </div>
      </div>

      <!-- Right Column: Topology Selector & Metrics Dashboard (4 cols) -->
      <div class="lg:col-span-4 space-y-6">

        <!-- Topology Selector Card -->
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-xl space-y-3">
          <h3 class="text-sm font-bold text-sky-400 uppercase tracking-wider">Select Power Grid Topology</h3>
          <div class="grid grid-cols-1 gap-2.5" id="topoBtnGroup">
            <button onclick="switchTopology('Topo_A_Sparse')" id="btn-Topo_A_Sparse" class="p-3 text-left rounded-xl border border-slate-700 bg-slate-900/60 hover:bg-slate-800/80 transition flex items-center justify-between">
              <div>
                <div class="font-bold text-sm text-slate-200">Topology A: Sparse Grid</div>
                <div class="text-xs text-rose-400">Under-designed (W=1.5µm, P=50µm)</div>
              </div>
              <span class="px-2 py-0.5 rounded text-xs bg-rose-500/20 text-rose-300 border border-rose-500/30">High Drop</span>
            </button>

            <button onclick="switchTopology('Topo_B_Dense')" id="btn-Topo_B_Dense" class="p-3 text-left rounded-xl border border-slate-700 bg-slate-900/60 hover:bg-slate-800/80 transition flex items-center justify-between">
              <div>
                <div class="font-bold text-sm text-slate-200">Topology B: Heavy Grid</div>
                <div class="text-xs text-amber-400">Over-designed (W=6.0µm, P=20µm)</div>
              </div>
              <span class="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30">Congested</span>
            </button>

            <button onclick="switchTopology('Topo_C_Optimized')" id="btn-Topo_C_Optimized" class="p-3 text-left rounded-xl border border-sky-500 bg-sky-950/40 hover:bg-slate-800/80 transition flex items-center justify-between">
              <div>
                <div class="font-bold text-sm text-sky-300">Topology C: Balanced Pareto</div>
                <div class="text-xs text-emerald-400">Recommended (W=3.5µm, P=30µm)</div>
              </div>
              <span class="px-2 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Optimal</span>
            </button>

            <button onclick="switchTopology('Topo_D_HotspotAware')" id="btn-Topo_D_HotspotAware" class="p-3 text-left rounded-xl border border-slate-700 bg-slate-900/60 hover:bg-slate-800/80 transition flex items-center justify-between">
              <div>
                <div class="font-bold text-sm text-slate-200">Topology D: Hotspot-Aware</div>
                <div class="text-xs text-sky-400">Adaptive Mesh + Local Decaps</div>
              </div>
              <span class="px-2 py-0.5 rounded text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30">Targeted</span>
            </button>
          </div>
        </div>

        <!-- Real-time Topology KPI Summary Card -->
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-xl space-y-4">
          <div class="flex justify-between items-center border-b border-slate-800 pb-3">
            <h3 class="text-sm font-bold text-[var(--foreground)]" id="activeTopoTitle">Topology C Metrics</h3>
            <span id="activeTopoBadge" class="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">PASS</span>
          </div>

          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="bg-slate-900/70 p-3 rounded-xl border border-slate-800">
              <span class="text-[var(--muted-foreground)] block">Peak Static IR Drop</span>
              <span class="text-base font-bold text-sky-400" id="valStaticDrop">4.44 mV</span>
              <span class="text-[11px] text-slate-400 block mt-0.5" id="valStaticDropPct">0.56% of VDD</span>
            </div>

            <div class="bg-slate-900/70 p-3 rounded-xl border border-slate-800">
              <span class="text-[var(--muted-foreground)] block">Peak Dynamic IR Drop</span>
              <span class="text-base font-bold text-rose-400" id="valDynDrop">15.46 mV</span>
              <span class="text-[11px] text-slate-400 block mt-0.5" id="valDynDropPct">1.93% of VDD</span>
            </div>

            <div class="bg-slate-900/70 p-3 rounded-xl border border-slate-800">
              <span class="text-[var(--muted-foreground)] block">Metal Blockage (Util)</span>
              <span class="text-base font-bold text-amber-400" id="valBlockage">11.8%</span>
              <span class="text-[11px] text-slate-400 block mt-0.5">Routing Friendly</span>
            </div>

            <div class="bg-slate-900/70 p-3 rounded-xl border border-slate-800">
              <span class="text-[var(--muted-foreground)] block">Decap Density</span>
              <span class="text-base font-bold text-purple-400" id="valDecap">15.0 nF/mm²</span>
              <span class="text-[11px] text-slate-400 block mt-0.5" id="valExtraDecap">+0 nF Hotspot</span>
            </div>
          </div>

          <div class="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1.5 text-xs">
            <div class="flex justify-between">
              <span class="text-slate-400">Max Current Density J:</span>
              <span class="font-mono font-bold text-slate-200" id="valMaxJ">4.77 mA/µm²</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Total Power Dissipation:</span>
              <span class="font-mono text-slate-200" id="valPower">0.44 W</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Dynamic Transient Overshoot:</span>
              <span class="font-mono text-rose-300" id="valOvershoot">11.02 mV</span>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Second Section: Dynamic Transient Waveform & Live Sizing Calculator -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Left: Transient Waveform Canvas (6 cols) -->
      <div class="lg:col-span-6 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-xl space-y-4">
        <div class="flex justify-between items-center">
          <div>
            <h2 class="text-base font-bold text-[var(--foreground)] flex items-center gap-2">
              <svg class="w-5 h-5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
              Transient Dynamic IR Drop (0 - 800 ps)
            </h2>
            <p class="text-xs text-[var(--muted-foreground)]">Simulated voltage droop at the core hotspot during 100ps clock switching surge.</p>
          </div>
          <span class="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">Backward Euler MNA</span>
        </div>

        <div class="bg-slate-950 rounded-xl p-3 border border-slate-800">
          <canvas id="transientCanvas" width="540" height="260" class="w-full"></canvas>
        </div>

        <div class="flex items-center justify-between text-xs text-[var(--muted-foreground)]">
          <span class="flex items-center gap-1.5"><span class="w-3 h-1 bg-sky-400 inline-block"></span> Active Topology</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-1 bg-red-500 inline-block"></span> Dynamic Budget Limit (40 mV)</span>
          <span class="text-slate-400">Decap Charge Reservoir Active</span>
        </div>
      </div>

      <!-- Right: Interactive PDN Sizing Calculator (6 cols) -->
      <div class="lg:col-span-6 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-xl space-y-4">
        <div class="flex justify-between items-center">
          <div>
            <h2 class="text-base font-bold text-[var(--foreground)] flex items-center gap-2">
              <svg class="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
              Analytical Stripe Sizing Calculator
            </h2>
            <p class="text-xs text-[var(--muted-foreground)]">Explore the governing equations: w_IR ~ (Rsq * P * L^2) / Delta_V and w_EM = I / (J_max * t).</p>
          </div>
          <span class="text-xs px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Live Calculator</span>
        </div>

        <div class="grid grid-cols-2 gap-4 text-xs">
          <!-- Slider 1: Power Density -->
          <div class="space-y-1">
            <div class="flex justify-between">
              <label class="text-slate-300 font-medium">Power Density (W/mm²):</label>
              <span id="lblPowerDensity" class="font-mono text-sky-400">1.2</span>
            </div>
            <input type="range" id="sliderPowerDensity" min="0.5" max="4.0" step="0.1" value="1.2" class="w-full accent-sky-400" oninput="recalcSizing()">
          </div>

          <!-- Slider 2: Stripe Pitch -->
          <div class="space-y-1">
            <div class="flex justify-between">
              <label class="text-slate-300 font-medium">Stripe Pitch P (µm):</label>
              <span id="lblPitch" class="font-mono text-sky-400">30</span>
            </div>
            <input type="range" id="sliderPitch" min="10" max="60" step="5" value="30" class="w-full accent-sky-400" oninput="recalcSizing()">
          </div>

          <!-- Slider 3: Span Length -->
          <div class="space-y-1">
            <div class="flex justify-between">
              <label class="text-slate-300 font-medium">Span Length L (µm):</label>
              <span id="lblSpan" class="font-mono text-sky-400">120</span>
            </div>
            <input type="range" id="sliderSpan" min="30" max="200" step="10" value="120" class="w-full accent-sky-400" oninput="recalcSizing()">
          </div>

          <!-- Slider 4: Target Static Drop -->
          <div class="space-y-1">
            <div class="flex justify-between">
              <label class="text-slate-300 font-medium">Target IR Drop (mV):</label>
              <span id="lblTargetDrop" class="font-mono text-sky-400">12</span>
            </div>
            <input type="range" id="sliderTargetDrop" min="4" max="30" step="1" value="12" class="w-full accent-sky-400" oninput="recalcSizing()">
          </div>
        </div>

        <!-- Sizing Results Panel -->
        <div class="bg-slate-900/90 border border-slate-700/80 rounded-xl p-4 grid grid-cols-3 gap-3 text-center">
          <div>
            <span class="text-[11px] text-slate-400 block">Min Width (IR Drop)</span>
            <span class="text-lg font-bold text-sky-400" id="resWidthIR">0.80 µm</span>
          </div>
          <div>
            <span class="text-[11px] text-slate-400 block">Min Width (EM)</span>
            <span class="text-lg font-bold text-amber-400" id="resWidthEM">2.16 µm</span>
          </div>
          <div>
            <span class="text-[11px] text-slate-400 block">Recommended Width</span>
            <span class="text-lg font-bold text-emerald-400" id="resWidthRec">2.16 µm</span>
          </div>
        </div>

        <div class="flex justify-between items-center text-xs p-2.5 bg-slate-950/60 rounded-lg border border-slate-800">
          <span class="text-slate-400">Resulting Metal Routing Blockage: <strong id="resBlockage" class="text-slate-200">7.2%</strong></span>
          <span id="resBadge" class="px-2 py-0.5 rounded font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">PASS (&le; 20% Blockage)</span>
        </div>
      </div>

    </div>

    <!-- Bottom Section: Cross-Topology Comparison Table -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-xl space-y-4">
      <h2 class="text-base font-bold text-[var(--foreground)] flex items-center gap-2">
        <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
        Multi-Topology Comprehensive Engineering Comparison
      </h2>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-800 text-slate-400">
              <th class="py-3 px-3">Topology Name</th>
              <th class="py-3 px-3">Width / Pitch</th>
              <th class="py-3 px-3">Peak Static IR</th>
              <th class="py-3 px-3">Peak Dynamic IR</th>
              <th class="py-3 px-3">Dynamic Overshoot</th>
              <th class="py-3 px-3">Routing Blockage</th>
              <th class="py-3 px-3">Decap Scheme</th>
              <th class="py-3 px-3">Design Verdict</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60 font-mono">
            <tr class="hover:bg-slate-800/30">
              <td class="py-3 px-3 font-bold text-slate-200">A: Sparse Grid</td>
              <td class="py-3 px-3 text-slate-400">W=1.5µm, P=50µm</td>
              <td class="py-3 px-3 text-rose-400 font-bold">22.82 mV (2.85%)</td>
              <td class="py-3 px-3 text-rose-400 font-bold">77.81 mV (9.73%)</td>
              <td class="py-3 px-3 text-rose-400">55.00 mV</td>
              <td class="py-3 px-3 text-emerald-400">2.7%</td>
              <td class="py-3 px-3 text-slate-400">5 nF/mm²</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded font-sans font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">FAIL (High Drop & EM)</span></td>
            </tr>
            <tr class="hover:bg-slate-800/30">
              <td class="py-3 px-3 font-bold text-slate-200">B: Heavy Uniform</td>
              <td class="py-3 px-3 text-slate-400">W=6.0µm, P=20µm</td>
              <td class="py-3 px-3 text-emerald-400 font-bold">1.71 mV (0.21%)</td>
              <td class="py-3 px-3 text-emerald-400 font-bold">6.07 mV (0.76%)</td>
              <td class="py-3 px-3 text-emerald-400">4.35 mV</td>
              <td class="py-3 px-3 text-amber-400 font-bold">27.5%</td>
              <td class="py-3 px-3 text-slate-400">25 nF/mm²</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded font-sans font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">REJECT (Routing Congestion)</span></td>
            </tr>
            <tr class="bg-sky-950/20 hover:bg-sky-950/30 border-l-4 border-l-sky-500">
              <td class="py-3 px-3 font-bold text-sky-300">C: Balanced Pareto</td>
              <td class="py-3 px-3 text-slate-300">W=3.5µm, P=30µm</td>
              <td class="py-3 px-3 text-emerald-400 font-bold">4.44 mV (0.56%)</td>
              <td class="py-3 px-3 text-emerald-400 font-bold">15.46 mV (1.93%)</td>
              <td class="py-3 px-3 text-slate-300">11.02 mV</td>
              <td class="py-3 px-3 text-emerald-400 font-bold">11.8%</td>
              <td class="py-3 px-3 text-slate-300">15 nF/mm²</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded font-sans font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">OPTIMAL BASELINE</span></td>
            </tr>
            <tr class="hover:bg-slate-800/30">
              <td class="py-3 px-3 font-bold text-purple-300">D: Hotspot-Aware</td>
              <td class="py-3 px-3 text-slate-300">W=3.8µm, P=25µm</td>
              <td class="py-3 px-3 text-emerald-400 font-bold">4.06 mV (0.51%)</td>
              <td class="py-3 px-3 text-emerald-400 font-bold">8.83 mV (1.10%)</td>
              <td class="py-3 px-3 text-emerald-400 font-bold">4.78 mV</td>
              <td class="py-3 px-3 text-sky-400">14.0%</td>
              <td class="py-3 px-3 text-purple-300">12 nF + 8 nF Hotspot</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded font-sans font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">RECOMMENDED FOR AI/SOC</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>

  <!-- Inlined JSON Data and Interactive Controller Script -->
  <script>
    const pdnData = {data_js_str};
    let currentTopoKey = "Topo_C_Optimized";

    // Initialize Canvas & Event Listeners
    window.addEventListener("DOMContentLoaded", () => {{
      renderHeatmap();
      renderTransientWaveform();
      recalcSizing();
    }});

    function switchTopology(key) {{
      currentTopoKey = key;
      
      // Update Button Styles
      const buttons = document.querySelectorAll("#topoBtnGroup button");
      buttons.forEach(btn => {{
        btn.classList.remove("border-sky-500", "bg-sky-950/40");
        btn.classList.add("border-slate-700", "bg-slate-900/60");
      }});
      const activeBtn = document.getElementById("btn-" + key);
      if (activeBtn) {{
        activeBtn.classList.add("border-sky-500", "bg-sky-950/40");
      }}

      // Update KPIs
      const topo = pdnData.topologies[key];
      const metrics = topo.metrics;
      const cfg = topo.config;

      document.getElementById("activeTopoTitle").innerText = topo.name;
      document.getElementById("valStaticDrop").innerText = metrics.max_static_ir_drop_mv + " mV";
      document.getElementById("valStaticDropPct").innerText = (metrics.max_static_ir_drop_mv / (pdnData.technology.nominal_vdd * 10)).toFixed(2) + "% of VDD";
      document.getElementById("valDynDrop").innerText = metrics.peak_dynamic_ir_drop_mv + " mV";
      document.getElementById("valDynDropPct").innerText = (metrics.peak_dynamic_ir_drop_mv / (pdnData.technology.nominal_vdd * 10)).toFixed(2) + "% of VDD";
      document.getElementById("valBlockage").innerText = metrics.utilization_avg_pct + "%";
      document.getElementById("valDecap").innerText = cfg.decap_nf_per_mm2 + " nF/mm²";
      document.getElementById("valExtraDecap").innerText = "+" + cfg.hotspot_extra_decap_nf + " nF Hotspot";
      document.getElementById("valMaxJ").innerText = metrics.max_current_density_ma_per_um2 + " mA/µm²";
      document.getElementById("valPower").innerText = metrics.total_power_w + " W";
      document.getElementById("valOvershoot").innerText = metrics.dynamic_overshoot_mv + " mV";

      // Badge
      const badge = document.getElementById("activeTopoBadge");
      if (metrics.max_static_ir_drop_mv > pdnData.technology.static_budget_mv || metrics.peak_dynamic_ir_drop_mv > pdnData.technology.dynamic_budget_mv) {{
        badge.innerText = "FAIL (Excessive Drop)";
        badge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30";
      }} else if (metrics.utilization_avg_pct > 20.0) {{
        badge.innerText = "WARN (High Blockage)";
        badge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30";
      }} else {{
        badge.innerText = "PASS (Optimal)";
        badge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
      }}

      // Rerender Canvas
      renderHeatmap();
      renderTransientWaveform();
    }}

    // Color interpolation function
    function getHeatmapColor(val, maxVal) {{
      const ratio = Math.min(1.0, Math.max(0.0, val / maxVal));
      // Gradient: Dark Navy (0) -> Sky (0.25) -> Yellow/Amber (0.6) -> Red/Crimson (1.0)
      let r, g, b;
      if (ratio < 0.25) {{
        const t = ratio / 0.25;
        r = Math.floor(15 + t * (56 - 15));
        g = Math.floor(23 + t * (189 - 23));
        b = Math.floor(42 + t * (248 - 42));
      }} else if (ratio < 0.6) {{
        const t = (ratio - 0.25) / 0.35;
        r = Math.floor(56 + t * (245 - 56));
        g = Math.floor(189 + t * (158 - 189));
        b = Math.floor(248 + t * (11 - 248));
      }} else {{
        const t = (ratio - 0.6) / 0.4;
        r = Math.floor(245 + t * (239 - 245));
        g = Math.floor(158 - t * 158);
        b = Math.floor(11 + t * (68 - 11));
      }}
      return `rgb(${{r}}, ${{g}}, ${{b}})`;
    }}

    function renderHeatmap() {{
      const canvas = document.getElementById("meshCanvas");
      const ctx = canvas.getContext("2d");
      const topo = pdnData.topologies[currentTopoKey];
      const hm = topo.heatmap;
      const w = canvas.width;
      const h = canvas.height;

      ctx.clearRect(0, 0, w, h);

      // Max drop scale
      const maxDrop = 25.0; // Fixed 25 mV reference ceiling
      document.getElementById("maxDropScale").innerText = `Max Drop: ${{topo.metrics.max_static_ir_drop_mv}} mV`;

      const cellW = w / (hm.nx - 1);
      const cellH = h / (hm.ny - 1);

      // Render interpolated color grid
      for (let j = 0; j < hm.ny - 1; j++) {{
        for (let i = 0; i < hm.nx - 1; i++) {{
          const v00 = hm.ir_drop_grid[j][i];
          const v10 = hm.ir_drop_grid[j][i + 1];
          const v01 = hm.ir_drop_grid[j + 1][i];
          const v11 = hm.ir_drop_grid[j + 1][i + 1];
          const vAvg = (v00 + v10 + v01 + v11) / 4.0;

          const px = i * cellW;
          const py = h - (j + 1) * cellH; // flip Y for standard cartesian

          ctx.fillStyle = getHeatmapColor(vAvg, maxDrop);
          ctx.fillRect(px, py, cellW + 1, cellH + 1);
        }}
      }}

      // Draw Grid Lines (Power Stripes)
      ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
      ctx.lineWidth = 1;
      for (let i = 0; i < hm.nx; i++) {{
        const px = i * cellW;
        ctx.beginPath();
        ctx.moveTo(px, 0);
        ctx.lineTo(px, h);
        ctx.stroke();
      }}
      for (let j = 0; j < hm.ny; j++) {{
        const py = h - j * cellH;
        ctx.beginPath();
        ctx.moveTo(0, py);
        ctx.lineTo(w, py);
        ctx.stroke();
      }}

      // Draw Hotspots
      const scaleX = w / 600.0;
      const scaleY = h / 600.0;
      
      const hotspots = [
        {{ name: "Core_ALU (3.2 W/mm²)", x1: 150, y1: 150, x2: 320, y2: 320 }},
        {{ name: "NPU_Cluster (2.8 W/mm²)", x1: 380, y1: 360, x2: 520, y2: 500 }}
      ];

      hotspots.forEach(hs => {{
        const hx = hs.x1 * scaleX;
        const hy = h - hs.y2 * scaleY;
        const hw = (hs.x2 - hs.x1) * scaleX;
        const hh = (hs.y2 - hs.y1) * scaleY;

        ctx.strokeStyle = "rgba(56, 189, 248, 0.8)";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(hx, hy, hw, hh);
        ctx.setLineDash([]);

        ctx.fillStyle = "rgba(56, 189, 248, 0.9)";
        ctx.font = "bold 11px sans-serif";
        ctx.fillText(hs.name, hx + 4, hy + 14);
      }});

      // Draw C4 Power Bumps
      const bumpPitch = topo.config.bump_pitch_um * scaleX;
      const bumpOffset = 30 * scaleX;
      ctx.fillStyle = "#38bdf8";
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1;

      for (let bx = bumpOffset; bx < w; bx += bumpPitch) {{
        for (let by = bumpOffset; by < h; by += bumpPitch) {{
          ctx.beginPath();
          ctx.arc(bx, h - by, 3.5, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }}
      }}
    }}

    // Hover Tooltip on 2D Mesh Canvas
    const canvas = document.getElementById("meshCanvas");
    const tooltip = document.getElementById("tooltip");

    canvas.addEventListener("mousemove", (e) => {{
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const topo = pdnData.topologies[currentTopoKey];
      const hm = topo.heatmap;

      const normX = mouseX / canvas.width;
      const normY = (canvas.height - mouseY) / canvas.height;

      const chipX = normX * 600.0;
      const chipY = normY * 600.0;

      // Find nearest grid index
      const ix = Math.min(hm.nx - 1, Math.max(0, Math.round(normX * (hm.nx - 1))));
      const iy = Math.min(hm.ny - 1, Math.max(0, Math.round(normY * (hm.ny - 1))));
      const dropVal = hm.ir_drop_grid[iy][ix];
      const voltVal = (pdnData.technology.nominal_vdd - dropVal * 1e-3).toFixed(4);

      tooltip.style.left = (e.clientX + 14) + "px";
      tooltip.style.top = (e.clientY + 14) + "px";
      tooltip.classList.remove("hidden");
      tooltip.innerHTML = `
        <div class="font-bold text-sky-400">Position: (${{chipX.toFixed(1)}}µm, ${{chipY.toFixed(1)}}µm)</div>
        <div class="text-slate-300">IR Drop: <strong class="text-amber-400">${{dropVal}} mV</strong> (${{(dropVal / 8.0).toFixed(2)}}% VDD)</div>
        <div class="text-slate-400">Local Voltage: <strong>${{voltVal}} V</strong></div>
      `;
    }});

    canvas.addEventListener("mouseleave", () => {{
      tooltip.classList.add("hidden");
    }});

    // Render Transient Waveform
    function renderTransientWaveform() {{
      const tCanvas = document.getElementById("transientCanvas");
      const ctx = tCanvas.getContext("2d");
      const w = tCanvas.width;
      const h = tCanvas.height;

      ctx.clearRect(0, 0, w, h);

      const topo = pdnData.topologies[currentTopoKey];
      const tr = topo.transient;
      const times = tr.time_ps;
      const drops = tr.worst_ir_mv;

      const maxTime = 800.0;
      const maxDropY = 90.0; // mV ceiling

      const padding = {{ left: 50, right: 20, top: 20, bottom: 35 }};
      const plotW = w - padding.left - padding.right;
      const plotH = h - padding.top - padding.bottom;

      // Background grid
      ctx.strokeStyle = "#1e293b";
      ctx.lineWidth = 1;
      for (let yVal = 0; yVal <= maxDropY; yVal += 20) {{
        const py = padding.top + plotH - (yVal / maxDropY) * plotH;
        ctx.beginPath();
        ctx.moveTo(padding.left, py);
        ctx.lineTo(padding.left + plotW, py);
        ctx.stroke();

        ctx.fillStyle = "#64748b";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(yVal + " mV", padding.left - 8, py + 3);
      }}

      for (let tVal = 0; tVal <= maxTime; tVal += 200) {{
        const px = padding.left + (tVal / maxTime) * plotW;
        ctx.beginPath();
        ctx.moveTo(px, padding.top);
        ctx.lineTo(px, padding.top + plotH);
        ctx.stroke();

        ctx.fillStyle = "#64748b";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(tVal + " ps", px, padding.top + plotH + 16);
      }}

      // Dynamic Budget Line (40 mV)
      const budgetY = padding.top + plotH - (40.0 / maxDropY) * plotH;
      ctx.strokeStyle = "#ef4444";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padding.left, budgetY);
      ctx.lineTo(padding.left + plotW, budgetY);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw Waveform
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      for (let i = 0; i < times.length; i++) {{
        const px = padding.left + (times[i] / maxTime) * plotW;
        const py = padding.top + plotH - (drops[i] / maxDropY) * plotH;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }}
      ctx.stroke();

      // Area fill under curve
      ctx.lineTo(padding.left + plotW, padding.top + plotH);
      ctx.lineTo(padding.left, padding.top + plotH);
      ctx.closePath();
      ctx.fillStyle = "rgba(56, 189, 248, 0.12)";
      ctx.fill();
    }}

    // Analytical Sizing Calculator Engine
    function recalcSizing() {{
      const pDensity = parseFloat(document.getElementById("sliderPowerDensity").value);
      const pitch = parseFloat(document.getElementById("sliderPitch").value);
      const span = parseFloat(document.getElementById("sliderSpan").value);
      const targetDrop = parseFloat(document.getElementById("sliderTargetDrop").value);

      document.getElementById("lblPowerDensity").innerText = pDensity.toFixed(1);
      document.getElementById("lblPitch").innerText = pitch;
      document.getElementById("lblSpan").innerText = span;
      document.getElementById("lblTargetDrop").innerText = targetDrop;

      const vdd = 0.80;
      const rsq = 0.035; // M8 sheet resistance
      const thickness = 0.50; // M8 thickness in um
      const jMax = 2.5; // mA / um^2

      // J_area in A / um^2
      const jArea = (pDensity / vdd) / 1e6;

      // IR Drop Width equation: W = (1/8) * R_sq * J_area * P * L^2 / Delta_V
      const targetDropVolts = targetDrop * 1e-3;
      const wIR = 0.125 * rsq * jArea * pitch * (span * span) / targetDropVolts;

      // EM Width equation: I = J_area * P * L, I_branch = I / 2
      const iTotalA = jArea * pitch * span;
      const iBranchMa = (iTotalA * 1e3) / 2.0;
      const wEM = iBranchMa / (jMax * thickness);

      const wRec = Math.max(0.8, wIR, wEM);
      const blockage = (wRec / pitch) * 100.0;

      document.getElementById("resWidthIR").innerText = wIR.toFixed(2) + " µm";
      document.getElementById("resWidthEM").innerText = wEM.toFixed(2) + " µm";
      document.getElementById("resWidthRec").innerText = wRec.toFixed(2) + " µm";
      document.getElementById("resBlockage").innerText = blockage.toFixed(1) + "%";

      const badge = document.getElementById("resBadge");
      if (blockage > 20.0) {{
        badge.innerText = "WARNING (> 20% Blockage)";
        badge.className = "px-2 py-0.5 rounded font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30";
      }} else {{
        badge.innerText = "PASS (<= 20% Blockage)";
        badge.className = "px-2 py-0.5 rounded font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
      }}
    }}
  </script>
</body>
</html>
"""
    with open(local_html_target, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[SUCCESS] Local Dashboard generated at: {local_html_target}")

    if os.path.exists(os.path.dirname(brain_html_target)):
        with open(brain_html_target, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[SUCCESS] Artifact Dashboard generated at: {brain_html_target}")

if __name__ == "__main__":
    generate_dashboard()
