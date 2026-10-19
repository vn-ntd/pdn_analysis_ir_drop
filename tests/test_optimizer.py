"""
Extended unit tests for PDN Parameter Optimizer and Pareto Explorer (v1.1.0).
"""
import unittest
from core.technology_specs import TechnologyConfig
from core.mna_mesh_solver import GridConfig, PowerHotspot
from core.optimizer import PDNOptimizer


class TestOptimizer(unittest.TestCase):
    def setUp(self):
        self.tech = TechnologyConfig()
        self.cfg = GridConfig(
            chip_width_um=200.0,
            chip_height_um=200.0,
            h_width_um=2.0,
            h_pitch_um=25.0,
            v_width_um=2.0,
            v_pitch_um=25.0,
            bump_pitch_um=100.0,
            background_power_w_per_mm2=0.8,
        )
        self.optimizer = PDNOptimizer(self.tech, self.cfg)

    def test_parametric_sweep(self):
        """Verify parameter sweep generates points with valid metrics."""
        widths = [2.0, 3.0]
        pitches = [25.0, 35.0]
        results = self.optimizer.sweep_width_and_pitch(widths, pitches)

        self.assertGreater(len(results), 0)
        for pt in results:
            self.assertGreater(pt.max_static_ir_drop_mv, 0)
            self.assertGreater(pt.metal_utilization_avg_pct, 0)
            self.assertIsInstance(pt.is_ir_compliant, bool)
            self.assertIsInstance(pt.is_em_compliant, bool)

    def test_pareto_optimal_selection(self):
        """Verify Pareto optimal point selection."""
        widths = [2.0, 3.0, 4.0]
        pitches = [25.0, 35.0]
        results = self.optimizer.sweep_width_and_pitch(widths, pitches)
        best = self.optimizer.find_pareto_optimal_design(results)

        self.assertIsNotNone(best)
        self.assertIsInstance(best.metal_utilization_avg_pct, float)

    def test_sweep_filters_absurd_widths(self):
        """Verify that widths >= 45% of pitch are excluded from sweep results."""
        widths = [1.0, 10.0, 20.0]  # 20.0 >= 0.45 * 25.0 => should be excluded
        pitches = [25.0]
        results = self.optimizer.sweep_width_and_pitch(widths, pitches)

        # All returned points should have utilization < 45%
        for pt in results:
            self.assertLess(pt.metal_utilization_avg_pct, 45.0,
                            "Absurd width (>45% blockage) should not be in sweep results")

    def test_sweep_sorted_by_fom(self):
        """Results must be sorted by figure_of_merit (ascending)."""
        widths = [1.5, 2.5, 3.5]
        pitches = [20.0, 30.0, 40.0]
        results = self.optimizer.sweep_width_and_pitch(widths, pitches)

        foms = [pt.figure_of_merit for pt in results]
        self.assertEqual(foms, sorted(foms),
                         "Sweep results must be sorted by figure_of_merit (ascending)")

    def test_pareto_returns_none_for_empty_input(self):
        """find_pareto_optimal_design on empty list returns None."""
        best = self.optimizer.find_pareto_optimal_design([])
        self.assertIsNone(best)

    def test_pareto_prefers_lower_utilization_among_compliant(self):
        """Among fully compliant designs, the one with lowest blockage is selected."""
        widths = [2.0, 3.0, 4.0, 5.0]
        pitches = [40.0, 50.0]
        results = self.optimizer.sweep_width_and_pitch(widths, pitches)

        compliant = [pt for pt in results
                     if pt.is_ir_compliant and pt.is_em_compliant and pt.is_utilization_compliant]

        if len(compliant) >= 2:
            best = self.optimizer.find_pareto_optimal_design(results)
            min_util_compliant = min(compliant, key=lambda x: x.metal_utilization_avg_pct)
            self.assertAlmostEqual(
                best.metal_utilization_avg_pct,
                min_util_compliant.metal_utilization_avg_pct,
                places=6,
                msg="Pareto selection should prefer minimum blockage among compliant designs",
            )


if __name__ == "__main__":
    unittest.main()
