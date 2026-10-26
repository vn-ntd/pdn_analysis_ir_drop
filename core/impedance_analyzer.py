"""
PDN Frequency-Domain Impedance Analyzer:
- Target Impedance calculation: Z_target = (Vdd * allowed_ripple) / delta_I
- Analytical frequency-domain impedance profile Z(f) across multi-decade frequency spectrum
- Anti-resonance LC peak identification between package bump inductance and on-chip decaps
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class ImpedanceProfileResult:
    frequencies_hz: np.ndarray
    z_magnitude_ohm: np.ndarray
    z_phase_deg: np.ndarray
    target_impedance_ohm: float
    peak_resonance_freq_hz: float
    peak_impedance_ohm: float
    is_compliant: bool
    resonant_frequency_ideal_hz: float


class PDNImpedanceAnalyzer:
    """
    Analyzes frequency-domain PDN impedance Z_PDN(f) and verifies compliance
    against Target Impedance Z_target across frequency spectrum (10 kHz - 5 GHz).
    """

    @staticmethod
    def calculate_target_impedance(
        vdd: float,
        allowed_ripple_pct: float,
        transient_step_current_a: float,
    ) -> float:
        """
        Calculates target impedance (Smith / Larry Smith equation):
          Z_target = (Vdd * ripple_pct) / Delta_I

        Args:
            vdd: Nominal supply voltage in Volts (e.g. 0.8V)
            allowed_ripple_pct: Allowed voltage droop fraction (e.g. 0.05 for 5%)
            transient_step_current_a: Transient load step in Amperes (e.g. 2.0A)

        Returns:
            Target impedance in Ohms
        """
        if transient_step_current_a <= 0:
            raise ValueError(f"Transient step current must be positive: got {transient_step_current_a}")
        voltage_ripple = vdd * allowed_ripple_pct
        return voltage_ripple / transient_step_current_a

    def calculate_impedance_spectrum(
        self,
        r_pkg_ohm: float,
        l_pkg_h: float,
        c_decap_f: float,
        esr_ohm: float = 0.002,
        l_grid_h: float = 5.0e-12,
        freq_min_hz: float = 1.0e5,
        freq_max_hz: float = 5.0e9,
        num_points: int = 500,
        target_z_ohm: Optional[float] = None,
    ) -> ImpedanceProfileResult:
        """
        Computes parallel frequency response between package supply branch (R_pkg + j*w*L_pkg)
        and on-chip decoupling capacitor network (ESR + 1/(j*w*C_decap) + j*w*L_grid).

        Anti-resonance occurs when package inductive reactance matches on-chip capacitive reactance:
          f_res = 1 / (2 * pi * sqrt(L_pkg * C_decap))
        """
        freqs = np.logspace(np.log10(freq_min_hz), np.log10(freq_max_hz), num_points)
        omega = 2.0 * np.pi * freqs

        # Package supply branch: Z_pkg(s) = R_pkg + s * L_pkg
        z_pkg = r_pkg_ohm + 1j * omega * l_pkg_h

        # On-chip Decap + grid branch: Z_decap(s) = ESR + 1 / (s * C) + s * L_grid
        z_decap = esr_ohm + (1.0 / (1j * omega * c_decap_f)) + 1j * omega * l_grid_h

        # Total parallel impedance: Z_PDN = (Z_pkg * Z_decap) / (Z_pkg + Z_decap)
        z_total = (z_pkg * z_decap) / (z_pkg + z_decap)
        z_mag = np.abs(z_total)
        z_phase = np.angle(z_total, deg=True)

        peak_idx = int(np.argmax(z_mag))
        peak_freq = float(freqs[peak_idx])
        peak_z = float(z_mag[peak_idx])

        # Ideal resonant frequency
        f_ideal = 1.0 / (2.0 * np.pi * np.sqrt(l_pkg_h * c_decap_f))

        target = target_z_ohm if target_z_ohm is not None else 0.020
        is_ok = bool(np.all(z_mag <= target))

        return ImpedanceProfileResult(
            frequencies_hz=freqs,
            z_magnitude_ohm=z_mag,
            z_phase_deg=z_phase,
            target_impedance_ohm=target,
            peak_resonance_freq_hz=peak_freq,
            peak_impedance_ohm=peak_z,
            is_compliant=is_ok,
            resonant_frequency_ideal_hz=f_ideal,
        )
