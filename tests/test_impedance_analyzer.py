"""
Unit tests for frequency-domain PDN impedance analysis and Z_target calculations.
"""
import unittest

import numpy as np

from core.impedance_analyzer import PDNImpedanceAnalyzer


class TestPDNImpedanceAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = PDNImpedanceAnalyzer()

    def test_target_impedance_calculation(self):
        """Z_target = (Vdd * ripple) / Delta_I: (0.8 * 0.05) / 2.0 = 0.020 Ohm."""
        z_target = self.analyzer.calculate_target_impedance(
            vdd=0.80, allowed_ripple_pct=0.05, transient_step_current_a=2.0
        )
        self.assertAlmostEqual(z_target, 0.020, places=6)

    def test_target_impedance_invalid_current_raises(self):
        """Negative or zero step current must raise ValueError."""
        with self.assertRaises(ValueError):
            self.analyzer.calculate_target_impedance(0.80, 0.05, 0.0)
        with self.assertRaises(ValueError):
            self.analyzer.calculate_target_impedance(0.80, 0.05, -1.5)

    def test_impedance_spectrum_shape_and_peak(self):
        """Verify impedance spectrum computation, LC resonance peak, and compliance."""
        # Realistic 7nm flip-chip package & decap parameters:
        # L_pkg = 20 pH (parallel bumps), C_decap = 15 nF
        res = self.analyzer.calculate_impedance_spectrum(
            r_pkg_ohm=0.005,
            l_pkg_h=20.0e-12,
            c_decap_f=15.0e-9,
            esr_ohm=0.002,
            target_z_ohm=0.030,
        )

        self.assertEqual(len(res.frequencies_hz), 500)
        self.assertEqual(len(res.z_magnitude_ohm), 500)
        self.assertGreater(res.peak_impedance_ohm, 0.0)
        self.assertGreater(res.peak_resonance_freq_hz, 1.0e6)
        self.assertLess(res.peak_resonance_freq_hz, 5.0e9)

        # Peak frequency should be reasonably close to ideal LC anti-resonance:
        # f_ideal = 1 / (2*pi*sqrt(L*C))
        f_ideal = 1.0 / (2.0 * np.pi * np.sqrt(20.0e-12 * 15.0e-9))
        self.assertAlmostEqual(res.resonant_frequency_ideal_hz, f_ideal, places=1)
        rel_diff = abs(res.peak_resonance_freq_hz - f_ideal) / f_ideal
        self.assertLess(rel_diff, 0.25)


if __name__ == "__main__":
    unittest.main()
