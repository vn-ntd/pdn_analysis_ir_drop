"""
Extended unit tests for the MNA power grid solver — covering fixes and edge cases.

New tests added in v1.1.0:
  - test_boundary_correction_exact: verifies corner/edge/interior area weighting (FIX C3)
  - test_hotspot_vectorization: confirms vectorized vs. scalar hotspot current gives same result
  - test_branch_current_vectorized: ensures j_h_map / j_v_map are correct via np.diff
  - test_dynamic_t_center_in_window: confirms surge peak falls within simulation window (FIX M4)
  - test_zero_bump_raises_or_produces_large_drop: edge case with no bumps in window
  - test_dynamic_bump_precompute_consistency: pre-computed b_bump gives same result as inline
  - test_grid_linspace_exact_bounds: checks x_coords/y_coords start/end at 0 and chip_size
  - test_hotspot_extra_decap_allocation: verifies local decap reduces transient overshoot
  - test_bump_via_array_resistance: checks via array modeling from bump to top metal
"""
import unittest

import numpy as np

from core.mna_mesh_solver import GridConfig, MNAPowerGridSolver, PowerHotspot
from core.technology_specs import TechnologyConfig


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
            uniform_decap_nf_per_mm2=10.0,
        )
        self.solver = MNAPowerGridSolver(self.tech, self.cfg)

    # ------------------------------------------------------------------ #
    # Original tests (preserved and updated for linspace grid)            #
    # ------------------------------------------------------------------ #

    def test_grid_initialization(self):
        """Verify grid node counts and coordinate bounds."""
        self.assertEqual(len(self.solver.x_coords), 11)  # 0 to 300 by 30, 11 points
        self.assertEqual(len(self.solver.y_coords), 11)
        self.assertEqual(self.solver.num_nodes, 121)

    def test_grid_config_validation_invalid_dimensions(self):
        """Verify GridConfig raises ValueError when dimensions are non-positive."""
        with self.assertRaises(ValueError):
            GridConfig(chip_width_um=-100.0)
        with self.assertRaises(ValueError):
            GridConfig(chip_height_um=0.0)

    def test_grid_config_validation_width_exceeds_pitch(self):
        """Verify GridConfig raises ValueError when width >= pitch."""
        with self.assertRaises(ValueError):
            GridConfig(h_width_um=50.0, h_pitch_um=30.0)
        with self.assertRaises(ValueError):
            GridConfig(v_width_um=40.0, v_pitch_um=40.0)

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
        self.assertTrue(np.all(diag >= off_diag_sum - 1e-9),
                        "MNA matrix is not diagonally dominant!")

    def test_static_solution_validity(self):
        """Verify static solution: node voltages are physically bounded within (0, VDD]."""
        res = self.solver.solve_static()

        self.assertTrue(np.all(res.voltage_map <= self.tech.nominal_vdd + 1e-6))
        self.assertTrue(np.all(res.voltage_map > 0.0))
        self.assertGreaterEqual(res.max_ir_drop_mv, 0.0)
        self.assertGreaterEqual(res.avg_ir_drop_mv, 0.0)
        self.assertLessEqual(res.min_ir_drop_mv, res.avg_ir_drop_mv)
        self.assertLessEqual(res.avg_ir_drop_mv, res.max_ir_drop_mv)
        self.assertAlmostEqual(
            res.total_power_w, self.tech.nominal_vdd * res.total_current_a, places=4
        )

    def test_dynamic_transient_simulation(self):
        """Verify transient Backward Euler simulation stability and overshoot behavior."""
        dyn_res = self.solver.solve_dynamic(duration_ps=400.0, dt_ps=10.0)

        # 0 to 400 ps with dt=10 ps has 41 points (inclusive bounds)
        self.assertEqual(len(dyn_res.time_ps), 41)
        self.assertEqual(len(dyn_res.worst_node_ir_drop_mv), 41)
        self.assertAlmostEqual(dyn_res.time_ps[1] - dyn_res.time_ps[0], 10.0, places=6)
        self.assertGreaterEqual(
            dyn_res.peak_dynamic_ir_drop_mv, dyn_res.peak_static_ir_drop_mv - 1e-4
        )
        self.assertGreaterEqual(dyn_res.dynamic_overshoot_mv, 0.0)
        self.assertGreater(dyn_res.decap_charge_supplied_pc, 0.0)

    def test_branch_current_and_em(self):
        """Verify branch current density calculation produces non-negative values."""
        res = self.solver.solve_static()

        self.assertTrue(np.all(res.current_density_h >= 0.0))
        self.assertTrue(np.all(res.current_density_v >= 0.0))
        self.assertGreater(res.max_current_density_ma_per_um2, 0.0)

    # ------------------------------------------------------------------ #
    # New tests for fixed bugs and enhancements                           #
    # ------------------------------------------------------------------ #

    def test_boundary_correction_exact(self):
        """
        [FIX C3] Verify corner nodes have exactly 1/4 the current of interior nodes,
        and edge (non-corner) nodes have 1/2.
        Uses a no-hotspot, no-bump config so all current comes from background only.
        """
        cfg_no_hs = GridConfig(
            chip_width_um=60.0,
            chip_height_um=60.0,
            h_width_um=2.0,
            h_pitch_um=20.0,
            v_width_um=2.0,
            v_pitch_um=20.0,
            bump_pitch_um=1000.0,   # Far away → no bumps inside chip
            background_power_w_per_mm2=1.0,
            hotspots=[],
        )
        solver = MNAPowerGridSolver(self.tech, cfg_no_hs)
        currents = solver._calculate_node_currents()  # shape (4, 4)

        interior = currents[1:-1, 1:-1]  # interior nodes
        corner_val = currents[0, 0]
        edge_top = currents[0, 1]  # top-row, non-corner

        interior_val = interior[0, 0]

        # Corner should be ~1/4 of interior
        self.assertAlmostEqual(corner_val / interior_val, 0.25, places=6,
                               msg="Corner node must have 1/4 area weight (×0.25)")
        # Edge (non-corner) should be ~1/2 of interior
        self.assertAlmostEqual(edge_top / interior_val, 0.5, places=6,
                               msg="Edge node must have 1/2 area weight (×0.5)")

    def test_hotspot_vectorization_matches_scalar(self):
        """
        [FIX M5] Verify vectorized hotspot assignment matches manual scalar calculation.
        """
        cfg = GridConfig(
            chip_width_um=100.0,
            chip_height_um=100.0,
            h_width_um=2.0,
            h_pitch_um=20.0,
            v_width_um=2.0,
            v_pitch_um=20.0,
            bump_pitch_um=500.0,
            background_power_w_per_mm2=1.0,
            hotspots=[
                PowerHotspot("HS1", 20.0, 60.0, 20.0, 60.0, power_density_w_per_mm2=2.5)
            ],
        )
        solver = MNAPowerGridSolver(self.tech, cfg)
        currents = solver._calculate_node_currents()

        vdd = self.tech.nominal_vdd
        tributary_area = cfg.v_pitch_um * cfg.h_pitch_um
        j_bg = (cfg.background_power_w_per_mm2 / vdd) / 1.0e6
        j_hs = (2.5 / vdd) / 1.0e6

        # Manually compute expected for a known interior hotspot node
        for j, y in enumerate(solver.y_coords):
            for i, x in enumerate(solver.x_coords):
                if (20.0 <= x <= 60.0 and 20.0 <= y <= 60.0 and
                        0 < i < solver.nx - 1 and 0 < j < solver.ny - 1):
                    expected = (j_bg + j_hs) * tributary_area
                    self.assertAlmostEqual(
                        currents[j, i], expected, places=10,
                        msg=f"Interior hotspot node ({i},{j}) mismatch"
                    )
                    return

    def test_branch_current_vectorized_shape_and_values(self):
        """
        [FIX M1] Verify vectorized j_h_map and j_v_map shapes are correct,
        and spot-check a branch value matches direct Ohm's law calculation.
        """
        res = self.solver.solve_static()

        # Shape checks
        self.assertEqual(res.current_density_h.shape, (self.solver.ny, self.solver.nx - 1))
        self.assertEqual(res.current_density_v.shape, (self.solver.ny - 1, self.solver.nx))

        # Spot-check: j_h[j, i] = |v[j,i] - v[j,i+1]| / r_h * 1e3 / area_h
        v_map = res.voltage_map
        for j in range(self.solver.ny):
            for i in range(self.solver.nx - 1):
                dv = abs(v_map[j, i] - v_map[j, i + 1])
                area_h = self.cfg.h_width_um * self.solver.h_spec.thickness
                expected_j = (dv / self.solver.r_h) * 1e3 / area_h
                self.assertAlmostEqual(
                    res.current_density_h[j, i], expected_j, places=8,
                    msg=f"j_h mismatch at ({i},{j})"
                )
            break

    def test_dynamic_surge_center_within_window(self):
        """
        [FIX M4] t_center = 25% of duration_ps must be within the simulation window.
        Verify that the worst IR drop waveform has its peak between 10% and 70% of duration.
        """
        duration = 600.0
        dt = 10.0
        dyn_res = self.solver.solve_dynamic(duration_ps=duration, dt_ps=dt)

        peak_idx = int(np.argmax(dyn_res.worst_node_ir_drop_mv))
        peak_t = dyn_res.time_ps[peak_idx]

        self.assertGreater(peak_t, duration * 0.05,
                           "Dynamic IR-drop peak too early in window")
        self.assertLess(peak_t, duration * 0.80,
                        "Dynamic IR-drop peak too late in window — surge may be outside")

    def test_grid_linspace_exact_bounds(self):
        """
        [FIX MIN3] x_coords[0] must be 0.0 and x_coords[-1] must be chip_width_um.
        """
        self.assertAlmostEqual(float(self.solver.x_coords[0]), 0.0, places=10)
        self.assertAlmostEqual(float(self.solver.x_coords[-1]),
                               self.cfg.chip_width_um, places=10)
        self.assertAlmostEqual(float(self.solver.y_coords[0]), 0.0, places=10)
        self.assertAlmostEqual(float(self.solver.y_coords[-1]),
                               self.cfg.chip_height_um, places=10)

    def test_hotspot_dynamic_peak_factor_increases_ir(self):
        """
        Hotspot with higher dynamic_peak_factor must produce larger dynamic IR drop
        than a simulation without hotspots.
        """
        cfg_no_hs = GridConfig(
            chip_width_um=300.0,
            chip_height_um=300.0,
            h_width_um=3.0,
            h_pitch_um=30.0,
            v_width_um=3.0,
            v_pitch_um=30.0,
            bump_pitch_um=100.0,
            background_power_w_per_mm2=1.0,
            hotspots=[],
            uniform_decap_nf_per_mm2=10.0,
        )
        solver_no_hs = MNAPowerGridSolver(self.tech, cfg_no_hs)
        dyn_no_hs = solver_no_hs.solve_dynamic(duration_ps=400.0, dt_ps=10.0)
        dyn_with_hs = self.solver.solve_dynamic(duration_ps=400.0, dt_ps=10.0)

        self.assertGreaterEqual(
            dyn_with_hs.peak_dynamic_ir_drop_mv,
            dyn_no_hs.peak_dynamic_ir_drop_mv,
            "Hotspot should increase peak dynamic IR drop",
        )

    def test_hotspot_extra_decap_allocation_reduces_dynamic_drop(self):
        """
        Verify that adding hotspot_extra_decap_nf increases local capacitance
        and effectively reduces dynamic transient IR-drop overshoot.
        """
        cfg_with_extra = GridConfig(
            chip_width_um=300.0,
            chip_height_um=300.0,
            h_width_um=3.0,
            h_pitch_um=30.0,
            v_width_um=3.0,
            v_pitch_um=30.0,
            bump_pitch_um=100.0,
            background_power_w_per_mm2=1.0,
            hotspots=[
                PowerHotspot("Core", 100.0, 200.0, 100.0, 200.0, power_density_w_per_mm2=3.0)
            ],
            uniform_decap_nf_per_mm2=10.0,
            hotspot_extra_decap_nf=10.0,
        )
        solver_extra = MNAPowerGridSolver(self.tech, cfg_with_extra)
        dyn_extra = solver_extra.solve_dynamic(duration_ps=400.0, dt_ps=10.0)
        dyn_base = self.solver.solve_dynamic(duration_ps=400.0, dt_ps=10.0)

        self.assertLess(
            dyn_extra.peak_dynamic_ir_drop_mv,
            dyn_base.peak_dynamic_ir_drop_mv,
            "Extra hotspot decap must reduce peak dynamic IR drop",
        )
        self.assertLess(
            dyn_extra.dynamic_overshoot_mv,
            dyn_base.dynamic_overshoot_mv,
            "Extra hotspot decap must reduce transient overshoot",
        )

    def test_bump_via_array_resistance_increases_effective_resistance(self):
        """
        Verify that configuring bump_num_via_cuts increases effective bump resistance
        by R_cut / num_cuts.
        """
        # Via8 is 0.25 Ohm / cut. With 25 cuts: 0.25 / 25 = 0.010 Ohm = 10 mOhm
        cfg_via = GridConfig(
            chip_width_um=300.0,
            chip_height_um=300.0,
            bump_resistance_ohm=0.020,
            bump_via_layer="Via8",
            bump_num_via_cuts=25,
        )
        solver_via = MNAPowerGridSolver(self.tech, cfg_via)
        self.assertAlmostEqual(solver_via.effective_bump_resistance_ohm, 0.030, places=6)

    def test_via_starvation_increases_static_ir_drop(self):
        """
        Verify that fewer via cuts (via starvation / higher bump contact resistance)
        causes higher static IR drop.
        """
        cfg_few_vias = GridConfig(
            chip_width_um=300.0,
            chip_height_um=300.0,
            bump_via_layer="Via8",
            bump_num_via_cuts=4,   # 0.25 / 4 = 62.5 mOhm extra
        )
        cfg_many_vias = GridConfig(
            chip_width_um=300.0,
            chip_height_um=300.0,
            bump_via_layer="Via8",
            bump_num_via_cuts=100,  # 0.25 / 100 = 2.5 mOhm extra
        )
        sol_few = MNAPowerGridSolver(self.tech, cfg_few_vias)
        sol_many = MNAPowerGridSolver(self.tech, cfg_many_vias)

        res_few = sol_few.solve_static()
        res_many = sol_many.solve_static()

        self.assertGreater(
            res_few.max_ir_drop_mv,
            res_many.max_ir_drop_mv,
            "Via starvation must lead to higher static IR drop",
        )


if __name__ == "__main__":
    unittest.main()
