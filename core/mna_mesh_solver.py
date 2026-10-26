"""
Modified Nodal Analysis (MNA) Power Grid Solver.
Performs:
1. Static IR-Drop 2D/Multi-layer Mesh Simulation (Sparse linear system G * V = I).
2. Dynamic IR-Drop Transient Simulation with Backward Euler and Decap charge-reservoir modeling.
3. Branch Current & Electromigration (EM) Current Density verification.
4. Support for Via array contact resistance (ViaSpec) between bumps and metal mesh.

Fixes applied (v1.1.0):
  - [C3] Boundary correction now uses exact area fractions: 0.25 for corners,
         0.5 for edges, 1.0 for interior — via numpy masks, no double-counting.
  - [M1] Branch current density (j_h_map, j_v_map) fully vectorized with np.diff.
  - [M2] Dynamic loop bump-term b_bump pre-computed once before time-step loop.
  - [M3] peak_multipliers computed via vectorized boolean masks.
  - [M4] t_center derived from duration_ps (25% of simulation window).
  - [M5] Hotspot current assignment vectorized with numpy boolean indexing.
  - [MIN3] Grid coordinates use np.linspace for exact floating-point spacing.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from core.technology_specs import TechnologyConfig


@dataclass
class PowerHotspot:
    name: str
    x_min_um: float
    x_max_um: float
    y_min_um: float
    y_max_um: float
    power_density_w_per_mm2: float
    dynamic_peak_factor: float = 3.5  # Peak dynamic current / DC current


@dataclass
class GridConfig:
    chip_width_um: float = 600.0
    chip_height_um: float = 600.0

    # Metal layer parameters for top/intermediate grid
    # Horizontal lines
    h_layer: str = "M9"
    h_width_um: float = 4.0
    h_pitch_um: float = 30.0

    # Vertical lines
    v_layer: str = "M8"
    v_width_um: float = 3.0
    v_pitch_um: float = 25.0

    # C4 Bump array configuration
    bump_pitch_um: float = 120.0
    bump_resistance_ohm: float = 0.025  # 25 mOhm per bump pad
    bump_offset_um: float = 30.0
    bump_via_layer: str = "Via8"
    bump_num_via_cuts: int = 0  # 0: raw bump resistance, >0: includes parallel via cuts

    # Power loading
    background_power_w_per_mm2: float = 0.8
    hotspots: List[PowerHotspot] = field(default_factory=list)

    # Decoupling capacitance
    uniform_decap_nf_per_mm2: float = 12.0  # Standard cell fill decaps
    hotspot_extra_decap_nf: float = 0.0

    def __post_init__(self) -> None:
        """Validate physical parameters of the PDN mesh configuration."""
        if self.chip_width_um <= 0 or self.chip_height_um <= 0:
            raise ValueError(
                f"Chip dimensions must be positive: got width={self.chip_width_um}, height={self.chip_height_um}"
            )
        if self.h_width_um <= 0 or self.v_width_um <= 0:
            raise ValueError(
                f"Stripe widths must be positive: got h_width={self.h_width_um}, v_width={self.v_width_um}"
            )
        if self.h_pitch_um <= self.h_width_um:
            raise ValueError(
                f"h_pitch ({self.h_pitch_um}) must be strictly greater than h_width ({self.h_width_um})"
            )
        if self.v_pitch_um <= self.v_width_um:
            raise ValueError(
                f"v_pitch ({self.v_pitch_um}) must be strictly greater than v_width ({self.v_width_um})"
            )
        if self.bump_pitch_um <= 0:
            raise ValueError(f"bump_pitch must be positive: got {self.bump_pitch_um}")
        if self.bump_resistance_ohm <= 0:
            raise ValueError(f"bump_resistance must be positive: got {self.bump_resistance_ohm}")


@dataclass
class StaticSimulationResult:
    grid_x: np.ndarray       # 1D grid x coordinates (um)
    grid_y: np.ndarray       # 1D grid y coordinates (um)
    voltage_map: np.ndarray  # 2D array of node voltages (V)
    ir_drop_map: np.ndarray  # 2D array of IR drop (mV)
    current_density_h: np.ndarray  # 2D branch current density (mA/um^2)
    current_density_v: np.ndarray  # 2D branch current density (mA/um^2)
    max_ir_drop_mv: float
    avg_ir_drop_mv: float
    min_ir_drop_mv: float
    worst_node_coord: Tuple[float, float]
    max_current_density_ma_per_um2: float
    em_violation_count: int
    total_power_w: float
    total_current_a: float
    metal_utilization_h_pct: float
    metal_utilization_v_pct: float


@dataclass
class DynamicSimulationResult:
    time_ps: np.ndarray
    worst_node_voltage: np.ndarray
    worst_node_ir_drop_mv: np.ndarray
    peak_dynamic_ir_drop_mv: float
    peak_static_ir_drop_mv: float
    dynamic_overshoot_mv: float
    decap_charge_supplied_pc: float


class MNAPowerGridSolver:
    def __init__(self, tech: TechnologyConfig, config: GridConfig) -> None:
        self.tech = tech
        self.config = config

        # Build coordinates using linspace for exact floating-point spacing (FIX MIN3)
        num_x = int(round(self.config.chip_width_um / self.config.v_pitch_um)) + 1
        num_y = int(round(self.config.chip_height_um / self.config.h_pitch_um)) + 1
        self.x_coords = np.linspace(0, self.config.chip_width_um, num_x)
        self.y_coords = np.linspace(0, self.config.chip_height_um, num_y)
        self.nx = len(self.x_coords)
        self.ny = len(self.y_coords)
        self.num_nodes = self.nx * self.ny

        # Layer specs
        self.h_spec = self.tech.layers[self.config.h_layer]
        self.v_spec = self.tech.layers[self.config.v_layer]

        # Compute branch resistances
        # Horizontal branch: length = delta_x = v_pitch, width = h_width
        self.r_h = self.h_spec.sheet_resistance * (self.config.v_pitch_um / self.config.h_width_um)
        # Vertical branch: length = delta_y = h_pitch, width = v_width
        self.r_v = self.v_spec.sheet_resistance * (self.config.h_pitch_um / self.config.v_width_um)

        # Effective bump connection resistance (bump pad + optional parallel via array)
        via_r = self.tech.get_via_array_resistance(
            self.config.bump_via_layer, self.config.bump_num_via_cuts
        )
        self.effective_bump_resistance_ohm = self.config.bump_resistance_ohm + via_r

        # Metal utilizations
        self.util_h = (self.config.h_width_um / self.config.h_pitch_um) * 100.0
        self.util_v = (self.config.v_width_um / self.config.v_pitch_um) * 100.0

    def _node_idx(self, i: int, j: int) -> int:
        """Map (ix, iy) to 1D flat index: row-major with x=column, y=row."""
        return j * self.nx + i

    def _get_bump_mask(self) -> np.ndarray:
        """Identify which nodes in the grid connect to C4 power bumps."""
        bump_mask = np.zeros((self.ny, self.nx), dtype=bool)
        bump_pitch = self.config.bump_pitch_um
        bump_offset = self.config.bump_offset_um

        # Map bump coordinates to nearest grid points
        bx_coords = np.arange(bump_offset, self.config.chip_width_um, bump_pitch)
        by_coords = np.arange(bump_offset, self.config.chip_height_um, bump_pitch)

        for by in by_coords:
            j = int(np.argmin(np.abs(self.y_coords - by)))
            for bx in bx_coords:
                i = int(np.argmin(np.abs(self.x_coords - bx)))
                bump_mask[j, i] = True

        return bump_mask

    def _calculate_node_currents(self) -> np.ndarray:
        """
        Calculate DC load current for each node based on background power and hotspots.

        Tributary area correction (FIX C3):
          - Interior nodes: full cell area (v_pitch * h_pitch)
          - Edge nodes (non-corner): half area (×0.5)
          - Corner nodes: quarter area (×0.25)

        Returns 2D array of currents in Amperes, shape (ny, nx).
        """
        tributary_area_um2 = self.config.v_pitch_um * self.config.h_pitch_um
        vdd = self.tech.nominal_vdd
        j_bg_a_per_um2 = (self.config.background_power_w_per_mm2 / vdd) / 1.0e6

        # Start with full tributary area for all nodes
        node_currents = np.full((self.ny, self.nx), j_bg_a_per_um2 * tributary_area_um2)

        # --- Vectorized Hotspot Current Addition (FIX M5) ---
        for hs in self.config.hotspots:
            j_hs_a_per_um2 = (hs.power_density_w_per_mm2 / vdd) / 1.0e6
            x_mask = (self.x_coords >= hs.x_min_um) & (self.x_coords <= hs.x_max_um)
            y_mask = (self.y_coords >= hs.y_min_um) & (self.y_coords <= hs.y_max_um)
            # Outer product to get 2D mask
            hs_mask_2d = np.outer(y_mask, x_mask)
            node_currents[hs_mask_2d] += j_hs_a_per_um2 * tributary_area_um2

        # --- Exact boundary area correction (FIX C3): use multiplicative mask ---
        # Build a weight map (1.0 = interior, 0.5 = edge, 0.25 = corner)
        area_weight = np.ones((self.ny, self.nx))

        # Edge rows/cols get factor 0.5
        area_weight[0, :] *= 0.5
        area_weight[-1, :] *= 0.5
        area_weight[:, 0] *= 0.5
        area_weight[:, -1] *= 0.5
        # After both passes, corner nodes have 0.5 * 0.5 = 0.25 — correct!

        node_currents *= area_weight
        return node_currents

    def build_mna_system(self) -> Tuple[sp.csr_matrix, np.ndarray, np.ndarray, np.ndarray]:
        """
        Construct sparse Conductance matrix G and RHS vector B.
        G * V = B

        Implements MNA stamp for a 2D resistive mesh with:
          - Horizontal branches (conductance g_h between adjacent x-nodes)
          - Vertical branches   (conductance g_v between adjacent y-nodes)
          - C4 bump sources     (conductance g_bump from VDD rail to node)
          - Distributed current loads (sunk from each node)
        """
        nx, ny = self.nx, self.ny
        n = self.num_nodes

        # Conductances
        g_h = 1.0 / self.r_h
        g_v = 1.0 / self.r_v
        g_bump = 1.0 / self.effective_bump_resistance_ohm

        bump_mask = self._get_bump_mask()
        node_currents = self._calculate_node_currents()

        # Preallocate sparse matrix entries (COO format)
        rows: List[int] = []
        cols: List[int] = []
        data: List[float] = []

        b = np.zeros(n)

        for j in range(ny):
            for i in range(nx):
                k = self._node_idx(i, j)
                diag_g = 0.0

                # West neighbor (i-1, j)
                if i > 0:
                    kw = self._node_idx(i - 1, j)
                    rows.append(k)
                    cols.append(kw)
                    data.append(-g_h)
                    diag_g += g_h

                # East neighbor (i+1, j)
                if i < nx - 1:
                    ke = self._node_idx(i + 1, j)
                    rows.append(k)
                    cols.append(ke)
                    data.append(-g_h)
                    diag_g += g_h

                # South neighbor (i, j-1)
                if j > 0:
                    ks = self._node_idx(i, j - 1)
                    rows.append(k)
                    cols.append(ks)
                    data.append(-g_v)
                    diag_g += g_v

                # North neighbor (i, j+1)
                if j < ny - 1:
                    kn = self._node_idx(i, j + 1)
                    rows.append(k)
                    cols.append(kn)
                    data.append(-g_v)
                    diag_g += g_v

                # C4 Bump connection (Dirichlet BC via conductance stamp)
                if bump_mask[j, i]:
                    diag_g += g_bump
                    b[k] += g_bump * self.tech.nominal_vdd

                # Load current (sunk from grid to logic cells)
                b[k] -= node_currents[j, i]

                # Diagonal entry
                rows.append(k)
                cols.append(k)
                data.append(diag_g)

        g_matrix = sp.coo_matrix((data, (rows, cols)), shape=(n, n)).tocsr()
        return g_matrix, b, bump_mask, node_currents

    def solve_static(self) -> StaticSimulationResult:
        """
        Solve static IR-drop and check electromigration current density.

        Branch current densities are computed via fully vectorized np.diff
        operations (FIX M1), giving O(1) numpy calls instead of nested loops.
        """
        g_mat, b_vec, bump_mask, node_currents = self.build_mna_system()

        # Solve linear system G * V = B using sparse direct solver
        v_flat = spla.spsolve(g_mat, b_vec)
        v_map = v_flat.reshape((self.ny, self.nx))

        # IR drop in millivolts
        ir_drop_map = (self.tech.nominal_vdd - v_map) * 1e3

        max_drop = float(np.max(ir_drop_map))
        avg_drop = float(np.mean(ir_drop_map))
        min_drop = float(np.min(ir_drop_map))

        # Find worst node
        worst_j, worst_i = np.unravel_index(np.argmax(ir_drop_map), ir_drop_map.shape)
        worst_coord = (float(self.x_coords[worst_i]), float(self.y_coords[worst_j]))

        # --- Vectorized Branch Current Density (FIX M1) ---
        # Horizontal branches: voltage diff between (i, j) and (i+1, j)
        # dv_h shape: (ny, nx-1)
        dv_h = np.abs(np.diff(v_map, axis=1))
        area_h_um2 = self.config.h_width_um * self.h_spec.thickness
        j_h_map = (dv_h / self.r_h) * 1e3 / area_h_um2  # mA / um^2

        # Vertical branches: voltage diff between (i, j) and (i, j+1)
        # dv_v shape: (ny-1, nx)
        dv_v = np.abs(np.diff(v_map, axis=0))
        area_v_um2 = self.config.v_width_um * self.v_spec.thickness
        j_v_map = (dv_v / self.r_v) * 1e3 / area_v_um2  # mA / um^2

        max_j = max(float(np.max(j_h_map)), float(np.max(j_v_map)))

        # Count EM violations
        em_h_viol = int(np.sum(j_h_map > self.h_spec.j_max_dc))
        em_v_viol = int(np.sum(j_v_map > self.v_spec.j_max_dc))

        total_curr = float(np.sum(node_currents))
        total_pwr = total_curr * self.tech.nominal_vdd

        return StaticSimulationResult(
            grid_x=self.x_coords,
            grid_y=self.y_coords,
            voltage_map=v_map,
            ir_drop_map=ir_drop_map,
            current_density_h=j_h_map,
            current_density_v=j_v_map,
            max_ir_drop_mv=max_drop,
            avg_ir_drop_mv=avg_drop,
            min_ir_drop_mv=min_drop,
            worst_node_coord=worst_coord,
            max_current_density_ma_per_um2=max_j,
            em_violation_count=em_h_viol + em_v_viol,
            total_power_w=total_pwr,
            total_current_a=total_curr,
            metal_utilization_h_pct=self.util_h,
            metal_utilization_v_pct=self.util_v,
        )

    def solve_dynamic(
        self,
        duration_ps: float = 800.0,
        dt_ps: float = 5.0,
        clock_period_ps: float = 500.0,
        switching_pulse_ps: float = 120.0,
    ) -> DynamicSimulationResult:
        """
        Solve transient dynamic IR drop using Backward Euler integration:
          (G + C / dt) * V(t + dt) = B(t + dt) + (C / dt) * V(t)

        Simulates clock switching surge with distributed decoupling capacitors.

        Optimizations applied:
          - b_bump pre-computed once, reused each timestep (FIX M2).
          - peak_multipliers computed with vectorized boolean masks (FIX M3).
          - t_center = 25% of duration_ps (FIX M4).
        """
        g_mat, b_static, bump_mask, node_currents_dc = self.build_mna_system()
        n = self.num_nodes

        # Initial DC steady-state
        v_dc = spla.spsolve(g_mat, b_static)

        # Build diagonal capacitance matrix C (Decap at each node)
        tributary_area_um2 = self.config.v_pitch_um * self.config.h_pitch_um
        # Uniform decap: nF/mm^2 -> Farads/um^2
        c_per_um2_f = (self.config.uniform_decap_nf_per_mm2 * 1e-9) / 1.0e6
        c_diag = np.full(n, c_per_um2_f * tributary_area_um2)

        # Add hotspot extra decaps if any
        if self.config.hotspot_extra_decap_nf > 0:
            extra_f_per_hs = self.config.hotspot_extra_decap_nf * 1e-9
            for hs in self.config.hotspots:
                x_mask = (self.x_coords >= hs.x_min_um) & (self.x_coords <= hs.x_max_um)
                y_mask = (self.y_coords >= hs.y_min_um) & (self.y_coords <= hs.y_max_um)
                hs_2d_mask = np.outer(y_mask, x_mask)
                hs_flat_indices = np.where(hs_2d_mask.flatten())[0]
                if len(hs_flat_indices) > 0:
                    add_c = extra_f_per_hs / len(hs_flat_indices)
                    c_diag[hs_flat_indices] += add_c

        c_mat = sp.diags(c_diag, format="csr")

        # Time stepping setup (exact dt_ps grid points: 0, dt, 2*dt, ..., duration)
        time_steps = int(round(duration_ps / dt_ps)) + 1
        t_vec = np.linspace(0, duration_ps, time_steps)
        dt_s = dt_ps * 1e-12

        # Effective system matrix: M = G + C / dt
        c_over_dt = c_mat / dt_s
        m_mat = (g_mat + c_over_dt).tocsc()

        # Pre-factorize M for fast transient stepping (LU factorization done once)
        lu_solver = spla.factorized(m_mat)

        # Find worst node index from static DC
        ir_dc = (self.tech.nominal_vdd - v_dc) * 1e3
        worst_idx = int(np.argmax(ir_dc))

        worst_v_wave = np.zeros(time_steps)
        worst_ir_wave = np.zeros(time_steps)

        v_curr = v_dc.copy()
        v_min_nodes = v_dc.copy()
        g_bump = 1.0 / self.effective_bump_resistance_ohm

        # --- Pre-compute bump RHS vector (FIX M2) ---
        # b_bump is constant across all timesteps: only load current changes
        b_bump = np.zeros(n)
        bump_flat_indices = np.where(bump_mask.flatten())[0]
        b_bump[bump_flat_indices] = g_bump * self.tech.nominal_vdd

        # Dynamic pulse shape: Gaussian current surge at clock edge
        # t_center at 25% of simulation window (FIX M4)
        t_center = duration_ps * 0.25
        sigma = switching_pulse_ps / 2.355  # FWHM → sigma

        # --- Vectorized peak multipliers (FIX M3) ---
        peak_multipliers_2d = np.ones((self.ny, self.nx))
        for hs in self.config.hotspots:
            x_mask = (self.x_coords >= hs.x_min_um) & (self.x_coords <= hs.x_max_um)
            y_mask = (self.y_coords >= hs.y_min_um) & (self.y_coords <= hs.y_max_um)
            hs_2d = np.outer(y_mask, x_mask)
            peak_multipliers_2d[hs_2d] = hs.dynamic_peak_factor

        peak_mult_flat = peak_multipliers_2d.flatten()
        i_dc_flat = node_currents_dc.flatten()

        for step, t in enumerate(t_vec):
            # Dynamic surge profile (Gaussian envelope)
            surge_factor = np.exp(-0.5 * ((t - t_center) / sigma) ** 2)

            # Current vector at time t: I_dc + (I_peak - I_dc) * surge_factor
            dynamic_factor = 1.0 + (peak_mult_flat - 1.0) * surge_factor
            i_load_t = i_dc_flat * dynamic_factor

            # Form RHS: B_bump - I_load(t) + (C/dt) * V(t)
            b_t = b_bump - i_load_t
            rhs = b_t + c_over_dt.dot(v_curr)

            # Solve next voltage state using pre-factorized LU
            v_curr = lu_solver(rhs)

            # Track minimum voltage achieved at each node
            v_min_nodes = np.minimum(v_min_nodes, v_curr)

            worst_v_wave[step] = v_curr[worst_idx]
            worst_ir_wave[step] = (self.tech.nominal_vdd - v_curr[worst_idx]) * 1e3

        peak_dyn_drop = float(np.max(worst_ir_wave))
        peak_static_drop = float(ir_dc[worst_idx])
        overshoot = peak_dyn_drop - peak_static_drop

        # Transient charge supplied by decaps (sum of C_k * Delta_V_k across all nodes)
        local_droops = np.maximum(0.0, v_dc - v_min_nodes)
        charge_pc = float(np.sum(c_diag * local_droops)) * 1e12

        return DynamicSimulationResult(
            time_ps=t_vec,
            worst_node_voltage=worst_v_wave,
            worst_node_ir_drop_mv=worst_ir_wave,
            peak_dynamic_ir_drop_mv=peak_dyn_drop,
            peak_static_ir_drop_mv=peak_static_drop,
            dynamic_overshoot_mv=overshoot,
            decap_charge_supplied_pc=charge_pc,
        )
