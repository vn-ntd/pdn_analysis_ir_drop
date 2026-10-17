"""
Analytical Sizing for Power Distribution Network (PDN):
- Electromigration (EM) minimum width calculation (Black's law limit).
- Static IR-drop analytical equations for stripes and rails.
- Decoupling capacitor (Decap) sizing for dynamic IR-drop suppression.
- Metal layer routing blockage (utilization) trade-offs.
"""
import math
from dataclasses import dataclass
from typing import Dict, Tuple
from core.technology_specs import TechnologyConfig, MetalLayerSpec

@dataclass
class AnalyticalSizingResult:
    layer_name: str
    target_ir_drop_v: float
    current_density_area_a_per_m2: float
    span_length_um: float
    pitch_um: float
    
    # Calculated values
    current_drawn_ma: float
    w_min_em_um: float
    w_min_ir_um: float
    recommended_width_um: float
    metal_utilization_pct: float
    actual_static_ir_drop_mv: float
    em_safety_margin: float
    is_em_compliant: bool
    is_ir_compliant: bool

class PDNAnalyticalSizer:
    def __init__(self, tech: TechnologyConfig):
        self.tech = tech

    def calculate_em_min_width(self, current_ma: float, layer: MetalLayerSpec, use_rms: bool = False) -> float:
        """
        Calculate minimum wire width to prevent electromigration.
        I_max = J_max * Area = J_max * (width * thickness)
        => width >= I / (J_max * thickness)
        
        Args:
            current_ma: Current in milliamperes (mA)
            layer: MetalLayerSpec
            use_rms: Whether to use RMS current density or DC
        Returns:
            Minimum width in micrometers (um)
        """
        j_limit = layer.j_max_rms if use_rms else layer.j_max_dc # mA / um^2
        # width = current_ma / (j_limit * thickness)
        w_em = current_ma / (j_limit * layer.thickness)
        return max(w_em, layer.min_width)

    def calculate_stripe_static_ir_drop(
        self,
        layer: MetalLayerSpec,
        width_um: float,
        pitch_um: float,
        span_length_um: float,
        power_density_w_per_mm2: float,
    ) -> Tuple[float, float]:
        """
        Calculates static IR drop along a stripe segment fed from both ends
        under uniformly distributed current load.
        
        Formula:
          J_area (A/um^2) = (P_density in W/mm^2) / (1e6 * Vdd)
          I_stripe (A) = J_area * pitch * span
          R_stripe (Ohm) = R_sq * (span / width)
          Delta_V = (1/8) * I_stripe * R_stripe (midpoint drop)
          
        Returns:
            (ir_drop_volts, current_drawn_ma)
        """
        # Convert power density to area current density
        # W/mm^2 / Vdd -> A/mm^2 -> A/um^2: 1 mm^2 = 1e6 um^2
        j_area_a_per_um2 = (power_density_w_per_mm2 / self.tech.nominal_vdd) / 1.0e6
        
        # Current flowing into this stripe segment (in Amperes)
        i_stripe_a = j_area_a_per_um2 * pitch_um * span_length_um
        i_stripe_ma = i_stripe_a * 1e3
        
        # Resistance of the stripe segment (Ohms)
        r_stripe = layer.sheet_resistance * (span_length_um / width_um)
        
        # Center-point static IR drop (both ends tied to low-impedance straps/bumps)
        # Delta V = 1/8 * I * R
        ir_drop_v = 0.125 * i_stripe_a * r_stripe
        
        return ir_drop_v, i_stripe_ma

    def calculate_required_width_for_ir(
        self,
        layer: MetalLayerSpec,
        pitch_um: float,
        span_length_um: float,
        power_density_w_per_mm2: float,
        target_ir_drop_v: float
    ) -> float:
        """
        Rearranging Delta_V = (1/8) * (J_area * P * L) * (R_sq * L / W):
          W = (1/8) * R_sq * J_area * P * L^2 / Delta_V
        """
        j_area_a_per_um2 = (power_density_w_per_mm2 / self.tech.nominal_vdd) / 1.0e6
        w_req = 0.125 * layer.sheet_resistance * j_area_a_per_um2 * pitch_um * (span_length_um ** 2) / target_ir_drop_v
        return max(w_req, layer.min_width)

    def size_power_stripe(
        self,
        layer_name: str,
        pitch_um: float,
        span_length_um: float,
        power_density_w_per_mm2: float,
        target_ir_drop_v: float = None
    ) -> AnalyticalSizingResult:
        """
        Complete analytical sizing for a power stripe or rail.
        """
        if target_ir_drop_v is None:
            target_ir_drop_v = self.tech.static_ir_budget_volts
            
        layer = self.tech.layers[layer_name]
        
        # 1. Minimum width for IR drop
        w_ir = self.calculate_required_width_for_ir(
            layer, pitch_um, span_length_um, power_density_w_per_mm2, target_ir_drop_v
        )
        
        # 2. Minimum width for EM (using full current entering stripe from half-span)
        j_area_a_per_um2 = (power_density_w_per_mm2 / self.tech.nominal_vdd) / 1.0e6
        total_current_ma = (j_area_a_per_um2 * pitch_um * span_length_um) * 1e3
        # Max current at ends of stripe is I_total / 2
        i_branch_max_ma = total_current_ma / 2.0
        w_em = self.calculate_em_min_width(i_branch_max_ma, layer)
        
        # Final recommended width
        recommended_w = max(w_ir, w_em, layer.min_width)
        recommended_w = min(recommended_w, layer.max_width) # Bound by DRC max width
        
        # Verify actual IR drop and EM with recommended width
        actual_ir_drop_v, i_ma = self.calculate_stripe_static_ir_drop(
            layer, recommended_w, pitch_um, span_length_um, power_density_w_per_mm2
        )
        
        utilization_pct = (recommended_w / pitch_um) * 100.0
        
        # EM safety factor
        actual_j = (i_ma / 2.0) / (recommended_w * layer.thickness) # mA / um^2
        em_margin = layer.j_max_dc / actual_j if actual_j > 0 else 999.0
        
        return AnalyticalSizingResult(
            layer_name=layer_name,
            target_ir_drop_v=target_ir_drop_v,
            current_density_area_a_per_m2=j_area_a_per_um2 * 1e12,
            span_length_um=span_length_um,
            pitch_um=pitch_um,
            current_drawn_ma=total_current_ma,
            w_min_em_um=w_em,
            w_min_ir_um=w_ir,
            recommended_width_um=recommended_w,
            metal_utilization_pct=utilization_pct,
            actual_static_ir_drop_mv=actual_ir_drop_v * 1e3,
            em_safety_margin=em_margin,
            is_em_compliant=(em_margin >= 1.0),
            is_ir_compliant=(actual_ir_drop_v <= target_ir_drop_v)
        )

    def size_decoupling_capacitance(
        self,
        peak_dynamic_current_a: float,
        average_dc_current_a: float,
        transient_duration_ps: float,
        target_dynamic_drop_v: float = None,
        package_inductance_per_bump_ph: float = 30.0,
        num_parallel_bumps: int = 25,
        rise_time_ps: float = 100.0,
    ) -> Dict[str, float]:
        """
        Sizing on-chip decoupling capacitors (Decap) to suppress dynamic IR drop
        and L*di/dt package supply bounce.
        
        Effective package inductance with N parallel VDD bumps:
          L_eff = L_bump / N_parallel_bumps
          
        Package inductive bounce:
          Delta_V_L = L_eff * (dI / dt) = L_eff * (I_peak - I_avg) / t_rise
        """
        if target_dynamic_drop_v is None:
            target_dynamic_drop_v = self.tech.dynamic_ir_budget_volts
            
        delta_i = max(0.0, peak_dynamic_current_a - average_dc_current_a)
        t_pulse_s = transient_duration_ps * 1e-12
        t_rise_s = rise_time_ps * 1e-12
        
        # Effective parallel inductance from bump array
        l_eff_h = (package_inductance_per_bump_ph * 1e-12) / max(1, num_parallel_bumps)
        
        # 1. Inductive bounce from package & bump array
        v_inductive_drop = l_eff_h * (delta_i / t_rise_s)
        
        # 2. Net dynamic voltage margin available for capacitive charge reservoir
        v_cap_margin = max(0.005, target_dynamic_drop_v - v_inductive_drop)
        
        # 3. Transient charge needed
        q_transient = 0.5 * delta_i * t_pulse_s # Coulombs
        
        # 4. Required decap capacitance
        c_decap_required_f = q_transient / v_cap_margin
        c_decap_nf = c_decap_required_f * 1e9
        
        return {
            "delta_i_peak_a": delta_i,
            "q_transient_pc": q_transient * 1e12,
            "l_eff_package_ph": l_eff_h * 1e12,
            "v_inductive_drop_mv": v_inductive_drop * 1e3,
            "net_cap_voltage_margin_mv": v_cap_margin * 1e3,
            "c_decap_required_nf": c_decap_nf,
            "is_inductive_dominant": (v_inductive_drop > target_dynamic_drop_v * 0.5)
        }
