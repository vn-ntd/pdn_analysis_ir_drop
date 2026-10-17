"""
Comprehensive Power Grid Analysis & IR-Drop Optimization Study:
1. Analytical sizing validation for EM and IR drop constraints.
2. Full MNA numerical mesh simulation comparing 4 realistic PDN topologies.
3. Dynamic IR-drop transient analysis (switching surges + Decap response).
4. Parametric sweep for the Pareto trade-off curve (Routing Blockage vs IR Drop).
5. High-resolution figure generation and JSON serialization for interactive UI.
"""
import os
import sys
import json
import numpy as np

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Reconfigure stdout to utf-8 on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from core.technology_specs import TechnologyConfig
from core.analytical_sizing import PDNAnalyticalSizer
from core.mna_mesh_solver import (
    MNAPowerGridSolver,
    GridConfig,
    PowerHotspot,
    StaticSimulationResult,
    DynamicSimulationResult
)
from core.optimizer import PDNOptimizer

def run_study():
    print("======================================================================")
    print("  POWER GRID ANALYSIS & IR-DROP OPTIMIZATION IN VLSI (7nm FINFET)")
    print("======================================================================")

    tech = TechnologyConfig()
    sizer = PDNAnalyticalSizer(tech)
    
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
    docs_img_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "images"))
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(docs_img_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. ANALYTICAL SIZING CALCULATIONS
    # -------------------------------------------------------------------------
    print("\n[PHASE 1] Analytical Sizing for Power Rails & Stripes:")
    print("-" * 65)
    
    # Example 1: Standard Cell M1 Power Rail
    # Typical stdcell row height: 0.64 um, cell span between M4 taps: 10 um
    # Local power density: 1.2 W/mm^2
    m1_sizing = sizer.size_power_stripe(
        layer_name="M1",
        pitch_um=0.640,
        span_length_um=10.0,
        power_density_w_per_mm2=1.2,
        target_ir_drop_v=0.008 # 8 mV budget on M1 rail
    )
    print(f"M1 Power Rail (span=10um, pitch=0.64um):")
    print(f"  - Target IR Drop: {m1_sizing.target_ir_drop_v*1e3:.1f} mV")
    print(f"  - Minimum W (IR Drop): {m1_sizing.w_min_ir_um*1e3:.1f} nm")
    print(f"  - Minimum W (EM):      {m1_sizing.w_min_em_um*1e3:.1f} nm")
    print(f"  - Recommended Width:   {m1_sizing.recommended_width_um*1e3:.1f} nm")
    print(f"  - Actual Static Drop:  {m1_sizing.actual_static_ir_drop_mv:.2f} mV")
    print(f"  - EM Safety Margin:    {m1_sizing.em_safety_margin:.2f}x (Compliant: {m1_sizing.is_em_compliant})")

    # Example 2: Intermediate M4 Stripe
    m4_sizing = sizer.size_power_stripe(
        layer_name="M4",
        pitch_um=8.0,
        span_length_um=50.0,
        power_density_w_per_mm2=1.2,
        target_ir_drop_v=0.010
    )
    print(f"\nM4 Intermediate Stripe (span=50um, pitch=8.0um):")
    print(f"  - Minimum W (IR):      {m4_sizing.w_min_ir_um:.3f} um")
    print(f"  - Minimum W (EM):      {m4_sizing.w_min_em_um:.3f} um")
    print(f"  - Recommended Width:   {m4_sizing.recommended_width_um:.3f} um")
    print(f"  - Metal Blockage:      {m4_sizing.metal_utilization_pct:.1f}%")
    print(f"  - Actual Static Drop:  {m4_sizing.actual_static_ir_drop_mv:.2f} mV")

    # Example 3: Top-Metal M8 Power Strap
    m8_sizing = sizer.size_power_stripe(
        layer_name="M8",
        pitch_um=30.0,
        span_length_um=120.0, # Span between C4 bumps
        power_density_w_per_mm2=1.2,
        target_ir_drop_v=0.012
    )
    print(f"\nM8 Global Power Strap (span=120um, pitch=30um):")
    print(f"  - Minimum W (IR):      {m8_sizing.w_min_ir_um:.2f} um")
    print(f"  - Minimum W (EM):      {m8_sizing.w_min_em_um:.2f} um")
    print(f"  - Recommended Width:   {m8_sizing.recommended_width_um:.2f} um")
    print(f"  - Metal Blockage:      {m8_sizing.metal_utilization_pct:.1f}%")
    print(f"  - Actual Static Drop:  {m8_sizing.actual_static_ir_drop_mv:.2f} mV")

    # Decap Sizing for Dynamic Surge with 30 parallel VDD bumps
    decap_calc = sizer.size_decoupling_capacitance(
        peak_dynamic_current_a=3.5,
        average_dc_current_a=0.9,
        transient_duration_ps=150.0,
        target_dynamic_drop_v=0.040, # 40 mV
        package_inductance_per_bump_ph=25.0,
        num_parallel_bumps=30,
        rise_time_ps=100.0
    )
    print(f"\nDecoupling Capacitance (Decap) Sizing:")
    print(f"  - Delta I Transient:   {decap_calc['delta_i_peak_a']:.2f} A")
    print(f"  - Transient Charge Q:  {decap_calc['q_transient_pc']:.2f} pC")
    print(f"  - L_eff Package:       {decap_calc['l_eff_package_ph']:.2f} pH")
    print(f"  - L*di/dt Package:     {decap_calc['v_inductive_drop_mv']:.2f} mV")
    print(f"  - Required Decap:      {decap_calc['c_decap_required_nf']:.2f} nF")

    # -------------------------------------------------------------------------
    # 2. DEFINING TOPOLOGIES FOR MNA MESH SIMULATION
    # -------------------------------------------------------------------------
    # Realistic test chip: 600 um x 600 um die with 2 high-power compute hotspots:
    # Hotspot 1: High-performance Core / ALU (150-320 um, 150-320 um), 3.2 W/mm^2
    # Hotspot 2: Neural Engine / NPU (380-520 um, 360-500 um), 2.8 W/mm^2
    hotspots = [
        PowerHotspot("Core_ALU", 150.0, 320.0, 150.0, 320.0, power_density_w_per_mm2=3.2, dynamic_peak_factor=4.0),
        PowerHotspot("NPU_Cluster", 380.0, 520.0, 360.0, 500.0, power_density_w_per_mm2=2.8, dynamic_peak_factor=3.5)
    ]
    
    topologies: Dict[str, Tuple[str, GridConfig]] = {
        "Topo_A_Sparse": (
            "Topology A: Sparse Grid (Under-designed)",
            GridConfig(
                chip_width_um=600.0,
                chip_height_um=600.0,
                h_layer="M9",
                h_width_um=1.5,
                h_pitch_um=50.0,
                v_layer="M8",
                v_width_um=1.2,
                v_pitch_um=50.0,
                bump_pitch_um=150.0,
                bump_resistance_ohm=0.035,
                background_power_w_per_mm2=0.7,
                hotspots=hotspots,
                uniform_decap_nf_per_mm2=5.0
            )
        ),
        "Topo_B_Dense": (
            "Topology B: Heavy Uniform Grid (Over-designed)",
            GridConfig(
                chip_width_um=600.0,
                chip_height_um=600.0,
                h_layer="M9",
                h_width_um=6.0,
                h_pitch_um=20.0,
                v_layer="M8",
                v_width_um=5.0,
                v_pitch_um=20.0,
                bump_pitch_um=100.0,
                bump_resistance_ohm=0.020,
                background_power_w_per_mm2=0.7,
                hotspots=hotspots,
                uniform_decap_nf_per_mm2=25.0
            )
        ),
        "Topo_C_Optimized": (
            "Topology C: Balanced Pareto Grid (Optimized)",
            GridConfig(
                chip_width_um=600.0,
                chip_height_um=600.0,
                h_layer="M9",
                h_width_um=3.5,
                h_pitch_um=30.0,
                v_layer="M8",
                v_width_um=3.0,
                v_pitch_um=25.0,
                bump_pitch_um=120.0,
                bump_resistance_ohm=0.025,
                background_power_w_per_mm2=0.7,
                hotspots=hotspots,
                uniform_decap_nf_per_mm2=15.0
            )
        ),
        "Topo_D_HotspotAware": (
            "Topology D: Hotspot-Aware Grid (Adaptive + Local Decap)",
            GridConfig(
                chip_width_um=600.0,
                chip_height_um=600.0,
                h_layer="M9",
                h_width_um=3.8,
                h_pitch_um=25.0,
                v_layer="M8",
                v_width_um=3.2,
                v_pitch_um=25.0,
                bump_pitch_um=120.0,
                bump_resistance_ohm=0.025,
                background_power_w_per_mm2=0.7,
                hotspots=hotspots,
                uniform_decap_nf_per_mm2=12.0,
                hotspot_extra_decap_nf=8.0 # +8 nF targeted directly at hotspots
            )
        ),
    }

    # -------------------------------------------------------------------------
    # 3. RUN NUMERICAL MNA SIMULATIONS
    # -------------------------------------------------------------------------
    print("\n[PHASE 2] Running Numerical MNA Mesh Simulations...")
    print("-" * 65)
    
    sim_results: Dict[str, Dict] = {}
    
    for key, (label, cfg) in topologies.items():
        solver = MNAPowerGridSolver(tech, cfg)
        static_res = solver.solve_static()
        dynamic_res = solver.solve_dynamic(duration_ps=800.0, dt_ps=5.0)
        
        sim_results[key] = {
            "label": label,
            "config": cfg,
            "static": static_res,
            "dynamic": dynamic_res
        }
        
        print(f"[{key}] {label}")
        print(f"  - Peak Static IR Drop:   {static_res.max_ir_drop_mv:.2f} mV ({static_res.max_ir_drop_mv/tech.nominal_vdd/10:.2f}% VDD)")
        print(f"  - Avg Static IR Drop:    {static_res.avg_ir_drop_mv:.2f} mV")
        print(f"  - Peak Dynamic IR Drop:  {dynamic_res.peak_dynamic_ir_drop_mv:.2f} mV ({dynamic_res.peak_dynamic_ir_drop_mv/tech.nominal_vdd/10:.2f}% VDD)")
        print(f"  - Dynamic Overshoot:     {dynamic_res.dynamic_overshoot_mv:.2f} mV")
        print(f"  - Metal Utilization:     H={static_res.metal_utilization_h_pct:.1f}%, V={static_res.metal_utilization_v_pct:.1f}%")
        print(f"  - Max Current Density J: {static_res.max_current_density_ma_per_um2:.2f} mA/um^2 (Limit={tech.layers['M8'].j_max_dc:.2f})")
        print(f"  - EM Violations:         {static_res.em_violation_count}")

    # -------------------------------------------------------------------------
    # 4. PARETO OPTIMIZATION SWEEP
    # -------------------------------------------------------------------------
    print("\n[PHASE 3] Running Pareto Parameter Sweep (Width vs Pitch)...")
    print("-" * 65)
    
    sweep_widths = [1.5, 2.5, 3.5, 4.5, 6.0]
    sweep_pitches = [20.0, 30.0, 40.0, 50.0, 60.0]
    
    optimizer = PDNOptimizer(tech, topologies["Topo_C_Optimized"][1])
    sweep_points = optimizer.sweep_width_and_pitch(sweep_widths, sweep_pitches)
    optimal_pt = optimizer.find_pareto_optimal_design(sweep_points)
    
    print(f"Swept {len(sweep_points)} design configurations.")
    if optimal_pt:
        print(f"Optimal Pareto Design Point:")
        print(f"  - Width: {optimal_pt.h_width_um:.1f} um, Pitch: {optimal_pt.h_pitch_um:.1f} um")
        print(f"  - Metal Blockage: {optimal_pt.metal_utilization_avg_pct:.1f}%")
        print(f"  - Max IR Drop:    {optimal_pt.max_static_ir_drop_mv:.2f} mV")
        print(f"  - EM Compliant:   {optimal_pt.is_em_compliant}")

    # -------------------------------------------------------------------------
    # 5. GENERATE HIGH-QUALITY MATPLOTLIB PLOTS
    # -------------------------------------------------------------------------
    print("\n[PHASE 4] Generating Publication-Quality Figures...")
    
    # 1. 4-Panel 2D IR-Drop Heatmap Comparison
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    vmax_drop = max(res["static"].max_ir_drop_mv for res in sim_results.values())
    
    for idx, (key, res) in enumerate(sim_results.items()):
        ax = axes[idx]
        static = res["static"]
        
        # 2D contour mesh
        x = static.grid_x
        y = static.grid_y
        X, Y = np.meshgrid(x, y)
        Z = static.ir_drop_map
        
        im = ax.contourf(X, Y, Z, levels=30, cmap="inferno", vmin=0, vmax=vmax_drop)
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("IR Drop (mV)", fontsize=11, fontweight="bold")
        
        # Mark C4 bumps
        solver_obj = MNAPowerGridSolver(tech, res["config"])
        bump_mask = solver_obj._get_bump_mask()
        for j in range(solver_obj.ny):
            for i in range(solver_obj.nx):
                if bump_mask[j, i]:
                    ax.plot(x[i], y[j], 'co', markersize=4, markeredgewidth=0.5, markeredgecolor='white')
                    
        # Annotate Hotspots
        for hs in res["config"].hotspots:
            rect = plt.Rectangle(
                (hs.x_min_um, hs.y_min_um),
                hs.x_max_um - hs.x_min_um,
                hs.y_max_um - hs.y_min_um,
                fill=False, edgecolor="cyan", linestyle="--", linewidth=1.5
            )
            ax.add_patch(rect)
            ax.text(hs.x_min_um + 5, hs.y_max_um - 15, hs.name, color="cyan", fontsize=9, fontweight="bold")
            
        ax.set_title(
            f"{res['label']}\nPeak IR Drop = {static.max_ir_drop_mv:.1f} mV | Blockage = {static.metal_utilization_h_pct:.1f}% | EM Violations = {static.em_violation_count}",
            fontsize=11, fontweight="bold"
        )
        ax.set_xlabel("X Coordinate (µm)", fontsize=10)
        ax.set_ylabel("Y Coordinate (µm)", fontsize=10)
        ax.set_aspect("equal")
        
    plt.tight_layout()
    heatmap_path = os.path.join(output_dir, "static_ir_drop_comparison.png")
    plt.savefig(heatmap_path, dpi=300)
    plt.savefig(os.path.join(docs_img_dir, "static_ir_drop_comparison.png"), dpi=300)
    plt.close()
    print(f"  [SAVED] {heatmap_path}")

    # 2. Dynamic IR-Drop Transient Waveforms
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = {
        "Topo_A_Sparse": "#d9534f",
        "Topo_B_Dense": "#5cb85c",
        "Topo_C_Optimized": "#0275d8",
        "Topo_D_HotspotAware": "#f0ad4e"
    }
    
    vdd_nominal = tech.nominal_vdd * 1e3 # in mV
    budget_line = tech.dynamic_ir_budget_volts * 1e3
    
    for key, res in sim_results.items():
        dyn = res["dynamic"]
        ax.plot(
            dyn.time_ps, dyn.worst_node_ir_drop_mv,
            label=f"{res['label']} (Peak={dyn.peak_dynamic_ir_drop_mv:.1f} mV)",
            color=colors[key], linewidth=2.5
        )
        
    ax.axhline(budget_line, color="red", linestyle=":", linewidth=2, label=f"Max Dynamic Budget ({budget_line:.0f} mV / 5% VDD)")
    ax.set_title("Transient Dynamic IR-Drop Response During Clock Edge Surge", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Time (picoseconds - ps)", fontsize=12)
    ax.set_ylabel("IR Drop at Worst Hotspot Node (mV)", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="upper right", framealpha=0.95, fontsize=10)
    
    plt.tight_layout()
    transient_path = os.path.join(output_dir, "dynamic_transient_waveforms.png")
    plt.savefig(transient_path, dpi=300)
    plt.savefig(os.path.join(docs_img_dir, "dynamic_transient_waveforms.png"), dpi=300)
    plt.close()
    print(f"  [SAVED] {transient_path}")

    # 3. Pareto Frontier: Routing Blockage vs Static IR Drop
    fig, ax = plt.subplots(figsize=(10, 6))
    
    util_vals = [pt.metal_utilization_avg_pct for pt in sweep_points]
    ir_vals = [pt.max_static_ir_drop_mv for pt in sweep_points]
    em_viol = [pt.em_violation_count > 0 for pt in sweep_points]
    
    # Non-compliant vs compliant points
    for u, ir, viol in zip(util_vals, ir_vals, em_viol):
        if viol:
            ax.scatter(u, ir, color="red", marker="x", s=90, alpha=0.8, label="EM Violation" if "EM Violation" not in [l.get_label() for l in ax.collections] else "")
        elif ir > tech.static_ir_budget_volts * 1e3:
            ax.scatter(u, ir, color="orange", marker="o", s=80, alpha=0.8, label="IR Exceeded" if "IR Exceeded" not in [l.get_label() for l in ax.collections] else "")
        else:
            ax.scatter(u, ir, color="#0275d8", marker="o", s=80, alpha=0.9, label="Compliant Design" if "Compliant Design" not in [l.get_label() for l in ax.collections] else "")
            
    # Mark Topologies
    for key, res in sim_results.items():
        st = res["static"]
        util = (st.metal_utilization_h_pct + st.metal_utilization_v_pct) / 2.0
        ax.scatter(util, st.max_ir_drop_mv, color="purple", s=180, edgecolors="black", linewidth=1.5, zorder=5)
        ax.annotate(
            key.replace("Topo_", ""),
            (util, st.max_ir_drop_mv),
            textcoords="offset points", xytext=(0, 10),
            ha='center', fontweight="bold", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.7)
        )
        
    ax.axhline(tech.static_ir_budget_volts * 1e3, color="red", linestyle="--", label=f"IR Budget Limit ({tech.static_ir_budget_volts*1e3:.0f} mV)")
    ax.axvline(20.0, color="green", linestyle="--", label="Max Routing Blockage Limit (20%)")
    
    ax.set_title("PDN Pareto Trade-off: Metal Routing Blockage vs Static IR Drop", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Metal Layer Utilization / Routing Blockage (%)", fontsize=12)
    ax.set_ylabel("Peak Static IR Drop (mV)", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="upper right", framealpha=0.95, fontsize=10)
    
    plt.tight_layout()
    pareto_path = os.path.join(output_dir, "pareto_frontier_blockage_vs_ir.png")
    plt.savefig(pareto_path, dpi=300)
    plt.savefig(os.path.join(docs_img_dir, "pareto_frontier_blockage_vs_ir.png"), dpi=300)
    plt.close()
    print(f"  [SAVED] {pareto_path}")

    # 4. Multi-Metric Summary Comparison Bar Chart
    fig, ax1 = plt.subplots(figsize=(11, 6))
    
    labels = ["A: Sparse", "B: Dense", "C: Balanced", "D: Hotspot-Aware"]
    keys = list(topologies.keys())
    
    x_indices = np.arange(len(labels))
    width = 0.25
    
    static_drops = [sim_results[k]["static"].max_ir_drop_mv for k in keys]
    dyn_drops = [sim_results[k]["dynamic"].peak_dynamic_ir_drop_mv for k in keys]
    utilizations = [(sim_results[k]["static"].metal_utilization_h_pct + sim_results[k]["static"].metal_utilization_v_pct)/2.0 for k in keys]
    
    rects1 = ax1.bar(x_indices - width, static_drops, width, label="Peak Static IR Drop (mV)", color="#337ab7")
    rects2 = ax1.bar(x_indices, dyn_drops, width, label="Peak Dynamic IR Drop (mV)", color="#d9534f")
    
    ax2 = ax1.twinx()
    rects3 = ax2.bar(x_indices + width, utilizations, width, label="Metal Blockage (%)", color="#5cb85c")
    
    ax1.set_ylabel("Voltage Drop (mV)", fontsize=12, fontweight="bold", color="#333333")
    ax2.set_ylabel("Routing Blockage (%)", fontsize=12, fontweight="bold", color="#5cb85c")
    ax1.set_xticks(x_indices)
    ax1.set_xticklabels(labels, fontsize=11, fontweight="bold")
    ax1.set_title("Multi-Metric Comparison Across Power Grid Topologies", fontsize=14, fontweight="bold", pad=12)
    
    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", framealpha=0.95)
    
    # Add values on top of bars
    for rect in rects1:
        h = rect.get_height()
        ax1.annotate(f"{h:.1f}", xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3),
                     textcoords="offset points", ha="center", va="bottom", fontsize=9)
    for rect in rects2:
        h = rect.get_height()
        ax1.annotate(f"{h:.1f}", xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3),
                     textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#a94442")
    for rect in rects3:
        h = rect.get_height()
        ax2.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3),
                     textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#3c763d")
                     
    plt.tight_layout()
    summary_path = os.path.join(output_dir, "topology_summary_barchart.png")
    plt.savefig(summary_path, dpi=300)
    plt.savefig(os.path.join(docs_img_dir, "topology_summary_barchart.png"), dpi=300)
    plt.close()
    print(f"  [SAVED] {summary_path}")

    # -------------------------------------------------------------------------
    # 6. EXPORT STRUCTURED JSON FOR GENERATIVE UI DASHBOARD
    # -------------------------------------------------------------------------
    json_data = {
        "technology": {
            "node": tech.node_name,
            "nominal_vdd": tech.nominal_vdd,
            "static_budget_mv": tech.static_ir_budget_volts * 1e3,
            "dynamic_budget_mv": tech.dynamic_ir_budget_volts * 1e3,
            "temp_c": tech.temp_celsius,
        },
        "analytical_sizing": {
            "m1": {
                "layer": "M1 Power Rail",
                "target_ir_mv": m1_sizing.target_ir_drop_v * 1e3,
                "w_ir_nm": m1_sizing.w_min_ir_um * 1e3,
                "w_em_nm": m1_sizing.w_min_em_um * 1e3,
                "rec_w_nm": m1_sizing.recommended_width_um * 1e3,
                "actual_ir_mv": m1_sizing.actual_static_ir_drop_mv,
                "em_margin": m1_sizing.em_safety_margin
            },
            "m4": {
                "layer": "M4 Intermediate Stripe",
                "target_ir_mv": m4_sizing.target_ir_drop_v * 1e3,
                "w_ir_um": m4_sizing.w_min_ir_um,
                "w_em_um": m4_sizing.w_min_em_um,
                "rec_w_um": m4_sizing.recommended_width_um,
                "actual_ir_mv": m4_sizing.actual_static_ir_drop_mv,
                "blockage_pct": m4_sizing.metal_utilization_pct
            },
            "m8": {
                "layer": "M8 Top Strap",
                "target_ir_mv": m8_sizing.target_ir_drop_v * 1e3,
                "w_ir_um": m8_sizing.w_min_ir_um,
                "w_em_um": m8_sizing.w_min_em_um,
                "rec_w_um": m8_sizing.recommended_width_um,
                "actual_ir_mv": m8_sizing.actual_static_ir_drop_mv,
                "blockage_pct": m8_sizing.metal_utilization_pct
            },
            "decap": decap_calc
        },
        "topologies": {}
    }
    
    for key, res in sim_results.items():
        st = res["static"]
        dyn = res["dynamic"]
        cfg = res["config"]
        
        # Subsample transient wave for compact JSON
        subsample = 4
        
        json_data["topologies"][key] = {
            "key": key,
            "name": res["label"],
            "config": {
                "h_width_um": cfg.h_width_um,
                "h_pitch_um": cfg.h_pitch_um,
                "v_width_um": cfg.v_width_um,
                "v_pitch_um": cfg.v_pitch_um,
                "bump_pitch_um": cfg.bump_pitch_um,
                "bump_resistance_ohm": cfg.bump_resistance_ohm,
                "decap_nf_per_mm2": cfg.uniform_decap_nf_per_mm2,
                "hotspot_extra_decap_nf": cfg.hotspot_extra_decap_nf
            },
            "metrics": {
                "max_static_ir_drop_mv": round(st.max_ir_drop_mv, 2),
                "avg_static_ir_drop_mv": round(st.avg_ir_drop_mv, 2),
                "peak_dynamic_ir_drop_mv": round(dyn.peak_dynamic_ir_drop_mv, 2),
                "dynamic_overshoot_mv": round(dyn.dynamic_overshoot_mv, 2),
                "utilization_h_pct": round(st.metal_utilization_h_pct, 2),
                "utilization_v_pct": round(st.metal_utilization_v_pct, 2),
                "utilization_avg_pct": round((st.metal_utilization_h_pct + st.metal_utilization_v_pct) / 2.0, 2),
                "max_current_density_ma_per_um2": round(st.max_current_density_ma_per_um2, 2),
                "em_violation_count": st.em_violation_count,
                "total_power_w": round(st.total_power_w, 2),
                "total_current_a": round(st.total_current_a, 2)
            },
            "heatmap": {
                "nx": len(st.grid_x),
                "ny": len(st.grid_y),
                "x_coords": [round(float(v), 1) for v in st.grid_x],
                "y_coords": [round(float(v), 1) for v in st.grid_y],
                # 2D list of IR drop values in mV
                "ir_drop_grid": [[round(float(val), 2) for val in row] for row in st.ir_drop_map]
            },
            "transient": {
                "time_ps": [round(float(t), 1) for t in dyn.time_ps[::subsample]],
                "worst_ir_mv": [round(float(v), 2) for v in dyn.worst_node_ir_drop_mv[::subsample]]
            }
        }
        
    json_path = os.path.join(output_dir, "pdn_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"  [SAVED] {json_path}")
    print("\n[SUCCESS] Power Grid Analysis study completed successfully!")

if __name__ == "__main__":
    run_study()
