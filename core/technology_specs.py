"""
Technology Specifications for Advanced Node Power Distribution Network (PDN).
Parameters calibrated for representative 7nm/16nm FinFET digital SoC.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class MetalLayerSpec:
    name: str
    direction: str          # 'horizontal' or 'vertical'
    sheet_resistance: float # Ohms per square (Ohm/sq)
    thickness: float        # Micrometers (um)
    min_width: float        # Micrometers (um)
    max_width: float        # Micrometers (um)
    min_pitch: float        # Micrometers (um)
    j_max_dc: float         # Max DC current density (mA/um^2) for EM
    j_max_rms: float        # Max RMS current density (mA/um^2) for EM

@dataclass
class ViaSpec:
    name: str
    resistance_per_cut: float # Ohms per single via cut
    cut_size: float           # um

@dataclass
class TechnologyConfig:
    node_name: str = "7nm FinFET Generic"
    nominal_vdd: float = 0.80  # Volts
    ir_drop_budget_static_pct: float = 0.025   # 2.5% VDD (= 20 mV)
    ir_drop_budget_dynamic_pct: float = 0.050  # 5.0% VDD (= 40 mV)
    temp_celsius: float = 105.0 # Operating junction temperature for EM

    # Metal Stack (Simplified PDN layers)
    layers: Dict[str, MetalLayerSpec] = None
    vias: Dict[str, ViaSpec] = None

    def __post_init__(self):
        if self.layers is None:
            self.layers = {
                # M1: Standard cell power rail
                "M1": MetalLayerSpec(
                    name="M1",
                    direction="horizontal",
                    sheet_resistance=0.85,    # 0.85 Ohm/sq (thin copper)
                    thickness=0.035,          # 35 nm = 0.035 um
                    min_width=0.040,          # 40 nm
                    max_width=0.120,          # 120 nm
                    min_pitch=0.640,          # Standard cell height track
                    j_max_dc=1.5,             # 1.5 mA/um^2
                    j_max_rms=3.0,
                ),
                # M4/M5: Intermediate power distribution stripes
                "M4": MetalLayerSpec(
                    name="M4",
                    direction="vertical",
                    sheet_resistance=0.18,
                    thickness=0.080,
                    min_width=0.100,
                    max_width=0.800,
                    min_pitch=2.000,
                    j_max_dc=1.8,
                    j_max_rms=3.5,
                ),
                "M5": MetalLayerSpec(
                    name="M5",
                    direction="horizontal",
                    sheet_resistance=0.15,
                    thickness=0.090,
                    min_width=0.120,
                    max_width=1.000,
                    min_pitch=3.000,
                    j_max_dc=1.8,
                    j_max_rms=3.5,
                ),
                # M8/M9: Top thick metal global power grid (power mesh)
                "M8": MetalLayerSpec(
                    name="M8",
                    direction="vertical",
                    sheet_resistance=0.035,   # Thick Cu strap
                    thickness=0.500,          # 0.5 um
                    min_width=0.800,
                    max_width=8.000,
                    min_pitch=10.00,
                    j_max_dc=2.5,
                    j_max_rms=5.0,
                ),
                "M9": MetalLayerSpec(
                    name="M9",
                    direction="horizontal",
                    sheet_resistance=0.020,   # Ultra-thick top metal
                    thickness=0.900,          # 0.9 um
                    min_width=1.000,
                    max_width=12.00,
                    min_pitch=15.00,
                    j_max_dc=2.8,
                    j_max_rms=5.5,
                ),
            }

        if self.vias is None:
            self.vias = {
                "Via1": ViaSpec("Via1", resistance_per_cut=12.0, cut_size=0.04),
                "Via4": ViaSpec("Via4", resistance_per_cut=4.0, cut_size=0.08),
                "Via8": ViaSpec("Via8", resistance_per_cut=0.25, cut_size=0.40),
            }

    @property
    def static_ir_budget_volts(self) -> float:
        return self.nominal_vdd * self.ir_drop_budget_static_pct

    @property
    def dynamic_ir_budget_volts(self) -> float:
        return self.nominal_vdd * self.ir_drop_budget_dynamic_pct
