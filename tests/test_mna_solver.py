"""
Unit tests for Modified Nodal Analysis (MNA) power grid numerical solver.
"""
import unittest
import numpy as np
import scipy.sparse as sp
from core.technology_specs import TechnologyConfig
from core.mna_mesh_solver import MNAPowerGridSolver, GridConfig, PowerHotspot

class TestMNAMeshSolver(unittest.TestCase):
    def setUp(self):
        self.tech = TechnologyConfig()
        self.cfg = GridConfig(
            chip_width_um=300.0,
            chip_height_um=300.0,
            h_width_um=3.0,
            h_pitch_um=30.0,
            v_width_um=3.0,
            v_pitch_um=30.0,
            bump_pitch_um=100.0,
            bump_resistance_ohm=0.025,
            background_power_w_per_mm2=1.0,
            hotspots=[
                PowerHotspot("Core", 100.0, 200.0, 100.0, 200.0, power_density_w_per_mm2=3.0)
            ],
            uniform_decap_nf_per_mm2=10.0
        )
        self.solver = MNAPowerGridSolver(self.tech, self.cfg)

    def test_grid_initialization(self):
        """Verify grid node counts and coordinate bounds."""
        self.assertEqual(len(self.solver.x_coords), 11) # 0 to 300 by 30
        self.assertEqual(len(self.solver.y_coords), 11)
        self.assertEqual(self.solver.num_nodes, 121)

    def test_mna_conductance_matrix_properties(self):
        """Verify MNA G matrix is sparse, square, diagonally dominant, and non-empty."""
        g_mat, b_vec, bump_mask, currents = self.solver.build_mna_system()
        
        self.assertEqual(g_mat.shape, (121, 121))
        self.assertEqual(len(b_vec), 121)
        self.assertGreater(np.sum(bump_mask), 0)
        
        # Check diagonal dominance: G_kk >= sum_{m != k} |G_km|
        g_dense = g_mat.toarray()
        diag = np.diag(g_dense)
        off_diag_sum = np.sum(np.abs(g_dense), axis=1) - np.abs(diag)
        self.assertTrue(np.all(diag >= off_diag_sum - 1e-9))

    def test_static_solution_validity(self):
        """Verify static solution: node voltages are physically bounded within (0, VDD]."""
        res = self.solver.solve_static()
        
        # Voltage map must be <= VDD and > 0
        self.assertTrue(np.all(res.voltage_map <= self.tech.nominal_vdd + 1e-6))
        self.assertTrue(np.all(res.voltage_map > 0.0))
        
        # IR drop must be non-negative
        self.assertGreaterEqual(res.max_ir_drop_mv, 0.0)
        self.assertGreaterEqual(res.avg_ir_drop_mv, 0.0)
        self.assertLessEqual(res.min_ir_drop_mv, res.avg_ir_drop_mv)
        self.assertLessEqual(res.avg_ir_drop_mv, res.max_ir_drop_mv)
        
        # Power calculation check: P = Vdd * I
        self.assertAlmostEqual(res.total_power_w, self.tech.nominal_vdd * res.total_current_a, places=4)

    def test_dynamic_transient_simulation(self):
        """Verify transient Backward Euler simulation stability and overshoot behavior."""
        dyn_res = self.solver.solve_dynamic(duration_ps=400.0, dt_ps=10.0)
        
        self.assertEqual(len(dyn_res.time_ps), 40)
        self.assertEqual(len(dyn_res.worst_node_ir_drop_mv), 40)
        
        # Dynamic peak drop must be >= static drop
        self.assertGreaterEqual(dyn_res.peak_dynamic_ir_drop_mv, dyn_res.peak_static_ir_drop_mv - 1e-4)
        self.assertGreaterEqual(dyn_res.dynamic_overshoot_mv, 0.0)
        
        # At start t=0, waveform should match static DC drop
        self.assertAlmostEqual(dyn_res.worst_node_ir_drop_mv[0], dyn_res.peak_static_ir_drop_mv, places=2)

    def test_branch_current_and_em(self):
        """Verify branch current density calculation."""
        res = self.solver.solve_static()
        
        # All current densities must be non-negative
        self.assertTrue(np.all(res.current_density_h >= 0.0))
        self.assertTrue(np.all(res.current_density_v >= 0.0))
        self.assertGreater(res.max_current_density_ma_per_um2, 0.0)

if __name__ == "__main__":
    unittest.main()
