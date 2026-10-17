"""
Unit tests for Analytical Sizing equations in PDN.
"""
import unittest
import math
from core.technology_specs import TechnologyConfig
from core.analytical_sizing import PDNAnalyticalSizer

class TestAnalyticalSizing(unittest.TestCase):
    def setUp(self):
        self.tech = TechnologyConfig()
        self.sizer = PDNAnalyticalSizer(self.tech)

    def test_em_min_width_dc(self):
        """Verify EM width equation: w >= I / (J_max * t)."""
        layer = self.tech.layers["M8"]
        current_ma = 10.0 # 10 mA
        # M8: j_max_dc = 2.5 mA/um^2, thickness = 0.5 um
        # Expected w = 10.0 / (2.5 * 0.5) = 8.0 um
        w = self.sizer.calculate_em_min_width(current_ma, layer, use_rms=False)
        self.assertAlmostEqual(w, 8.0, places=4)

    def test_em_min_width_clamped_to_min_drc(self):
        """Verify that EM width respects minimum DRC width of the metal layer."""
        layer = self.tech.layers["M8"]
        tiny_current_ma = 0.001
        w = self.sizer.calculate_em_min_width(tiny_current_ma, layer)
        self.assertEqual(w, layer.min_width)

    def test_static_ir_drop_formula_consistency(self):
        """
        Verify that calculating required width for a target IR drop,
        and then recalculating IR drop with that width yields the exact target drop
        when w_req > min_width.
        """
        layer = self.tech.layers["M8"]
        pitch = 40.0 # um
        span = 300.0 # um
        power_density = 2.0 # W/mm^2
        target_drop_v = 0.010 # 10 mV

        w_req = self.sizer.calculate_required_width_for_ir(
            layer, pitch, span, power_density, target_drop_v
        )
        # Verify w_req is above min_width
        self.assertGreater(w_req, layer.min_width)

        ir_drop_actual, i_ma = self.sizer.calculate_stripe_static_ir_drop(
            layer, w_req, pitch, span, power_density
        )

        self.assertAlmostEqual(ir_drop_actual, target_drop_v, places=6)
        self.assertGreater(i_ma, 0.0)

    def test_static_ir_drop_min_width_clamping(self):
        """Verify that when unconstrained w_req < min_width, actual drop is strictly better."""
        layer = self.tech.layers["M8"]
        pitch = 20.0
        span = 50.0
        power_density = 0.5
        target_drop_v = 0.030 # 30 mV (very loose)

        w_req = self.sizer.calculate_required_width_for_ir(
            layer, pitch, span, power_density, target_drop_v
        )
        self.assertEqual(w_req, layer.min_width)

        ir_drop_actual, _ = self.sizer.calculate_stripe_static_ir_drop(
            layer, w_req, pitch, span, power_density
        )
        self.assertLessEqual(ir_drop_actual, target_drop_v)

    def test_size_power_stripe_compliance(self):
        """Test full analytical sizing structure and compliance flags."""
        result = self.sizer.size_power_stripe(
            layer_name="M8",
            pitch_um=30.0,
            span_length_um=120.0,
            power_density_w_per_mm2=1.0,
            target_ir_drop_v=0.015
        )

        self.assertEqual(result.layer_name, "M8")
        self.assertGreater(result.recommended_width_um, 0)
        self.assertGreater(result.metal_utilization_pct, 0)
        self.assertLess(result.metal_utilization_pct, 100)
        self.assertTrue(result.is_ir_compliant)
        self.assertTrue(result.is_em_compliant)

    def test_decap_sizing(self):
        """Test decoupling capacitance calculation with parallel bump inductance."""
        res = self.sizer.size_decoupling_capacitance(
            peak_dynamic_current_a=3.0,
            average_dc_current_a=1.0,
            transient_duration_ps=150.0,
            target_dynamic_drop_v=0.040,
            package_inductance_per_bump_ph=30.0,
            num_parallel_bumps=30,
            rise_time_ps=100.0
        )

        self.assertEqual(res["delta_i_peak_a"], 2.0)
        self.assertAlmostEqual(res["q_transient_pc"], 150.0, places=3)
        self.assertAlmostEqual(res["l_eff_package_ph"], 1.0, places=3)
        self.assertAlmostEqual(res["v_inductive_drop_mv"], 20.0, places=3)
        self.assertGreater(res["c_decap_required_nf"], 0.0)

if __name__ == "__main__":
    unittest.main()
