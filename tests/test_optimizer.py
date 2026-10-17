"""
Unit tests for PDN Parameter Optimizer and Pareto Explorer.
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
            background_power_w_per_mm2=0.8
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

if __name__ == "__main__":
    unittest.main()
