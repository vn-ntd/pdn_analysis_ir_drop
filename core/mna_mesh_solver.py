"""
Modified Nodal Analysis (MNA) Power Grid Solver.
Performs:
1. Static IR-Drop 2D/Multi-layer Mesh Simulation (Sparse linear system G * V = I).
2. Dynamic IR-Drop Transient Simulation with Backward Euler and Decap charge-reservoir modeling.
3. Branch Current & Electromigration (EM) Current Density verification.
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from core.technology_specs import TechnologyConfig

@dataclass
class PowerHotspot:
    name: str
    x_min_um: float
    x_max_um: float
    y_min_um: float
    y_max_um: float
    power_density_w_per_mm2: float
    dynamic_peak_factor: float = 3.5 # Peak dynamic current / DC current

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
    bump_resistance_ohm: float = 0.025 # 25 mOhm per bump pad
    bump_offset_um: float = 30.0
    
    # Power loading
    background_power_w_per_mm2: float = 0.8
    hotspots: List[PowerHotspot] = field(default_factory=list)
    
    # Decoupling capacitance
    uniform_decap_nf_per_mm2: float = 12.0 # Standard cell fill decaps
    hotspot_extra_decap_nf: float = 0.0

@dataclass
class StaticSimulationResult:
    grid_x: np.ndarray # 1D grid x coordinates (um)
    grid_y: np.ndarray # 1D grid y coordinates (um)
    voltage_map: np.ndarray # 2D array of node voltages (V)
    ir_drop_map: np.ndarray # 2D array of IR drop (mV)
    current_density_h: np.ndarray # 2D branch current density (mA/um^2)
    current_density_v: np.ndarray # 2D branch current density (mA/um^2)
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
    def __init__(self, tech: TechnologyConfig, config: GridConfig):
        self.tech = tech
        self.config = config
        
        # Build coordinates
        self.x_coords = np.arange(0, self.config.chip_width_um + 1e-6, self.config.v_pitch_um)
        self.y_coords = np.arange(0, self.config.chip_height_um + 1e-6, self.config.h_pitch_um)
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
        
        # Metal utilizations
        self.util_h = (self.config.h_width_um / self.config.h_pitch_um) * 100.0
        self.util_v = (self.config.v_width_um / self.config.v_pitch_um) * 100.0

    def _node_idx(self, i: int, j: int) -> int:
        """Map (ix, iy) to 1D index."""
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
        Returns 2D array of currents in Amperes.
        """
        node_currents = np.zeros((self.ny, self.nx))
        # Tributary area of each internal node
        tributary_area_um2 = self.config.v_pitch_um * self.config.h_pitch_um
        
        vdd = self.tech.nominal_vdd
        
        # Background current
        j_bg_a_per_um2 = (self.config.background_power_w_per_mm2 / vdd) / 1.0e6
        node_currents[:, :] = j_bg_a_per_um2 * tributary_area_um2
        
        # Add Hotspots
        for hs in self.config.hotspots:
            j_hs_a_per_um2 = (hs.power_density_w_per_mm2 / vdd) / 1.0e6
            for j, y in enumerate(self.y_coords):
                if hs.y_min_um <= y <= hs.y_max_um:
                    for i, x in enumerate(self.x_coords):
                        if hs.x_min_um <= x <= hs.x_max_um:
                            node_currents[j, i] += j_hs_a_per_um2 * tributary_area_um2
                            
        # Boundary correction (edge and corner nodes have 1/2 or 1/4 area)
        node_currents[0, :] *= 0.5
        node_currents[-1, :] *= 0.5
        node_currents[:, 0] *= 0.5
        node_currents[:, -1] *= 0.5
        
        return node_currents

    def build_mna_system(self) -> Tuple[sp.csr_matrix, np.ndarray, np.ndarray, np.ndarray]:
        """
        Construct sparse Conductance matrix G and RHS vector B.
        G * V = B
        """
        nx, ny = self.nx, self.ny
        n = self.num_nodes
        
        # Conductances
        g_h = 1.0 / self.r_h
        g_v = 1.0 / self.r_v
        g_bump = 1.0 / self.config.bump_resistance_ohm
        
        bump_mask = self._get_bump_mask()
        node_currents = self._calculate_node_currents()
        
        # Preallocate sparse matrix entries (COO format)
        rows = []
        cols = []
        data = []
        
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
                    
                # C4 Bump connection
                if bump_mask[j, i]:
                    diag_g += g_bump
                    b[k] += g_bump * self.tech.nominal_vdd
                    
                # Load current (sunk from grid to logic)
                b[k] -= node_currents[j, i]
                
                # Diagonal entry
                rows.append(k)
                cols.append(k)
                data.append(diag_g)
                
        g_matrix = sp.coo_matrix((data, (rows, cols)), shape=(n, n)).tocsr()
        return g_matrix, b, bump_mask, node_currents

    def solve_static(self) -> StaticSimulationResult:
        """
        Solve static IR-drop and check electromigration current density across all branches.
        """
        g_mat, b_vec, bump_mask, node_currents = self.build_mna_system()
        
        # Solve linear system G * V = B using sparse LU solver
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
        
        # Calculate branch currents and EM current densities
        # Horizontal branches: between (i, j) and (i+1, j)
        j_h_map = np.zeros((self.ny, self.nx - 1))
        # Area of H stripe = width * thickness (um^2)
        area_h_um2 = self.config.h_width_um * self.h_spec.thickness
        for j in range(self.ny):
            for i in range(self.nx - 1):
                dv = abs(v_map[j, i] - v_map[j, i + 1])
                curr_ma = (dv / self.r_h) * 1e3
                j_h_map[j, i] = curr_ma / area_h_um2 # mA / um^2
                
        # Vertical branches: between (i, j) and (i, j+1)
        j_v_map = np.zeros((self.ny - 1, self.nx))
        area_v_um2 = self.config.v_width_um * self.v_spec.thickness
        for j in range(self.ny - 1):
            for i in range(self.nx):
                dv = abs(v_map[j, i] - v_map[j + 1, i])
                curr_ma = (dv / self.r_v) * 1e3
                j_v_map[j, i] = curr_ma / area_v_um2
                
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
            metal_utilization_v_pct=self.util_v
        )

    def solve_dynamic(
        self,
        duration_ps: float = 800.0,
        dt_ps: float = 5.0,
        clock_period_ps: float = 500.0,
        switching_pulse_ps: float = 120.0
    ) -> DynamicSimulationResult:
        """
        Solve transient dynamic IR drop using Backward Euler integration:
          (G + C / dt) * V(t + dt) = B(t + dt) + (C / dt) * V(t)
        Simulates clock switching surge with distributed decoupling capacitors.
        """
        g_mat, b_static, bump_mask, node_currents_dc = self.build_mna_system()
        n = self.num_nodes
        
        # Initial DC state
        v_dc = spla.spsolve(g_mat, b_static)
        
        # Build diagonal capacitance matrix C (Decap at each node)
        tributary_area_um2 = self.config.v_pitch_um * self.config.h_pitch_um
        # Uniform decap: nF/mm^2 -> Farads/um^2
        c_per_um2_f = (self.config.uniform_decap_nf_per_mm2 * 1e-9) / 1.0e6
        c_diag = np.full(n, c_per_um2_f * tributary_area_um2)
        
        # Add hotspot extra decaps if any
        if self.config.hotspot_extra_decap_nf > 0:
            extra_f_per_hs = (self.config.hotspot_extra_decap_nf * 1e-9)
            for hs in self.config.hotspots:
                # Find nodes within hotspot
                hs_node_indices = []
                for j, y in enumerate(self.y_coords):
                    if hs.y_min_um <= y <= hs.y_max_um:
                        for i, x in enumerate(self.x_coords):
                            if hs.x_min_um <= x <= hs.x_max_um:
                                hs_node_indices.append(self._node_idx(i, j))
                if hs_node_indices:
                    add_c = extra_f_per_hs / len(hs_node_indices)
                    c_diag[hs_node_indices] += add_c
                    
        c_mat = sp.diags(c_diag, format="csr")
        
        # Time stepping setup
        time_steps = int(duration_ps / dt_ps)
        t_vec = np.linspace(0, duration_ps, time_steps)
        dt_s = dt_ps * 1e-12
        
        # Effective system matrix: M = G + C / dt
        c_over_dt = c_mat / dt_s
        m_mat = (g_mat + c_over_dt).tocsc()
        
        # Pre-factorize M for lightning-fast transient stepping
        lu_solver = spla.factorized(m_mat)
        
        # Find worst node index from static DC
        ir_dc = (self.tech.nominal_vdd - v_dc) * 1e3
        worst_idx = int(np.argmax(ir_dc))
        
        worst_v_wave = np.zeros(time_steps)
        worst_ir_wave = np.zeros(time_steps)
        
        v_curr = v_dc.copy()
        g_bump = 1.0 / self.config.bump_resistance_ohm
        
        # Dynamic pulse shape: Gaussian current surge at clock edge (e.g. t = 200 ps)
        t_center = 200.0
        sigma = switching_pulse_ps / 2.355 # FWHM
        
        # Peak multipliers per node: hotspots have higher dynamic switching factors
        peak_multipliers = np.ones((self.ny, self.nx))
        for hs in self.config.hotspots:
            for j, y in enumerate(self.y_coords):
                if hs.y_min_um <= y <= hs.y_max_um:
                    for i, x in enumerate(self.x_coords):
                        if hs.x_min_um <= x <= hs.x_max_um:
                            peak_multipliers[j, i] = hs.dynamic_peak_factor
                            
        peak_mult_flat = peak_multipliers.flatten()
        i_dc_flat = node_currents_dc.flatten()
        
        for step, t in enumerate(t_vec):
            # Dynamic surge profile
            surge_factor = np.exp(-0.5 * ((t - t_center) / sigma) ** 2)
            
            # Current vector at time t: I_dc + (I_peak - I_dc) * surge_factor
            dynamic_factor = 1.0 + (peak_mult_flat - 1.0) * surge_factor
            i_load_t = i_dc_flat * dynamic_factor
            
            # Form RHS: B(t) + (C / dt) * V(t)
            # Reconstruct B(t)
            b_t = np.zeros(n)
            # Add bump terms
            for j in range(self.ny):
                for i in range(self.nx):
                    if bump_mask[j, i]:
                        k = self._node_idx(i, j)
                        b_t[k] += g_bump * self.tech.nominal_vdd
                        
            b_t -= i_load_t
            
            rhs = b_t + c_over_dt.dot(v_curr)
            
            # Solve next voltage state
            v_next = lu_solver(rhs)
            v_curr = v_next
            
            worst_v_wave[step] = v_curr[worst_idx]
            worst_ir_wave[step] = (self.tech.nominal_vdd - v_curr[worst_idx]) * 1e3
            
        peak_dyn_drop = float(np.max(worst_ir_wave))
        peak_static_drop = float(ir_dc[worst_idx])
        overshoot = peak_dyn_drop - peak_static_drop
        
        # Transient charge supplied by decaps
        total_decap_f = float(np.sum(c_diag))
        charge_pc = total_decap_f * (overshoot * 1e-3) * 1e12
        
        return DynamicSimulationResult(
            time_ps=t_vec,
            worst_node_voltage=worst_v_wave,
            worst_node_ir_drop_mv=worst_ir_wave,
            peak_dynamic_ir_drop_mv=peak_dyn_drop,
            peak_static_ir_drop_mv=peak_static_drop,
            dynamic_overshoot_mv=overshoot,
            decap_charge_supplied_pc=charge_pc
        )
