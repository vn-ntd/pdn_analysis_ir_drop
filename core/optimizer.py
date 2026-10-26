"""
PDN Parameter Optimizer & Trade-Off Explorer.
Explores the Pareto frontier between IR-drop, Electromigration margins,
and Metal Layer Routing Blockage (Utilization).
"""
from dataclasses import dataclass
from typing import List, Optional

from core.mna_mesh_solver import GridConfig, MNAPowerGridSolver
from core.technology_specs import TechnologyConfig


@dataclass
class OptimizationPoint:
    h_width_um: float
    h_pitch_um: float
    v_width_um: float
    v_pitch_um: float
    metal_utilization_avg_pct: float
    max_static_ir_drop_mv: float
    avg_static_ir_drop_mv: float
    max_current_density_ma_per_um2: float
    em_violation_count: int
    is_ir_compliant: bool
    is_em_compliant: bool
    is_utilization_compliant: bool
    figure_of_merit: float # Combined cost score (lower is better)

class PDNOptimizer:
    def __init__(self, tech: TechnologyConfig, base_config: GridConfig):
        self.tech = tech
        self.base_config = base_config

    def sweep_width_and_pitch(
        self,
        widths: List[float],
        pitches: List[float],
        max_allowed_utilization_pct: float = 20.0
    ) -> List[OptimizationPoint]:
        """
        Sweep stripe width and pitch symmetrically across horizontal and vertical layers
        to build the IR-Drop vs Routing Blockage Pareto curve.
        """
        results: List[OptimizationPoint] = []
        static_budget_mv = self.tech.static_ir_budget_volts * 1e3

        for p in pitches:
            for w in widths:
                if w >= p * 0.45: # Filter out physically absurd or DRC violating widths (>45% blockage)
                    continue

                cfg = GridConfig(
                    chip_width_um=self.base_config.chip_width_um,
                    chip_height_um=self.base_config.chip_height_um,
                    h_layer=self.base_config.h_layer,
                    h_width_um=w,
                    h_pitch_um=p,
                    v_layer=self.base_config.v_layer,
                    v_width_um=w,
                    v_pitch_um=p,
                    bump_pitch_um=self.base_config.bump_pitch_um,
                    bump_resistance_ohm=self.base_config.bump_resistance_ohm,
                    background_power_w_per_mm2=self.base_config.background_power_w_per_mm2,
                    hotspots=self.base_config.hotspots,
                    uniform_decap_nf_per_mm2=self.base_config.uniform_decap_nf_per_mm2
                )

                solver = MNAPowerGridSolver(self.tech, cfg)
                res = solver.solve_static()

                util_avg = (res.metal_utilization_h_pct + res.metal_utilization_v_pct) / 2.0
                ir_ok = (res.max_ir_drop_mv <= static_budget_mv)
                em_ok = (res.em_violation_count == 0)
                util_ok = (util_avg <= max_allowed_utilization_pct)

                # Figure of Merit: penalize IR drop, high metal blockage, and heavy penalty for EM violations
                # Lower score is better
                ir_penalty = max(0.0, res.max_ir_drop_mv - static_budget_mv) * 10.0
                em_penalty = res.em_violation_count * 1000.0
                fom = res.max_ir_drop_mv * 1.0 + util_avg * 1.5 + ir_penalty + em_penalty

                pt = OptimizationPoint(
                    h_width_um=w,
                    h_pitch_um=p,
                    v_width_um=w,
                    v_pitch_um=p,
                    metal_utilization_avg_pct=util_avg,
                    max_static_ir_drop_mv=res.max_ir_drop_mv,
                    avg_static_ir_drop_mv=res.avg_ir_drop_mv,
                    max_current_density_ma_per_um2=res.max_current_density_ma_per_um2,
                    em_violation_count=res.em_violation_count,
                    is_ir_compliant=ir_ok,
                    is_em_compliant=em_ok,
                    is_utilization_compliant=util_ok,
                    figure_of_merit=fom
                )
                results.append(pt)

        # Sort by figure of merit
        results.sort(key=lambda x: x.figure_of_merit)
        return results

    def find_pareto_optimal_design(
        self,
        sweep_results: List[OptimizationPoint]
    ) -> Optional[OptimizationPoint]:
        """
        Finds the design that is fully compliant (IR <= budget, EM = 0, Utilization <= max)
        with the minimal routing blockage.
        """
        compliant = [
            pt for pt in sweep_results
            if pt.is_ir_compliant and pt.is_em_compliant and pt.is_utilization_compliant
        ]

        if not compliant:
            # If none compliant with strict util, pick best compliant with IR & EM
            relaxed = [pt for pt in sweep_results if pt.is_ir_compliant and pt.is_em_compliant]
            if relaxed:
                return min(relaxed, key=lambda x: x.metal_utilization_avg_pct)
            return sweep_results[0] if sweep_results else None

        # Select one with lowest metal utilization among compliant
        return min(compliant, key=lambda x: (x.metal_utilization_avg_pct, x.max_static_ir_drop_mv))
