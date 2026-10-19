"""
Test for CLI argument parsing in run_pdn_study.py (v1.1.0).
Covers FIX M7: argparse integration for chip-size, background-power, etc.
"""
import unittest
import sys
import os

# Ensure project root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulations.run_pdn_study import parse_args


class TestCLIArguments(unittest.TestCase):
    """Tests for the argparse CLI interface in run_pdn_study."""

    def _parse(self, argv):
        """Helper: parse a list of CLI argument strings."""
        old_argv = sys.argv
        sys.argv = ["run_pdn_study.py"] + argv
        try:
            return parse_args()
        finally:
            sys.argv = old_argv

    def test_defaults(self):
        """Verify all defaults match expected values."""
        args = self._parse([])
        self.assertEqual(args.chip_size, 600.0)
        self.assertEqual(args.background_power, 0.7)
        self.assertEqual(args.duration_ps, 800.0)
        self.assertEqual(args.dt_ps, 5.0)
        self.assertIsNone(args.output_dir)
        self.assertFalse(args.no_plots)
        self.assertFalse(args.quiet)

    def test_chip_size_override(self):
        """--chip-size correctly overrides default."""
        args = self._parse(["--chip-size", "400.0"])
        self.assertEqual(args.chip_size, 400.0)

    def test_background_power_override(self):
        """--background-power correctly overrides default."""
        args = self._parse(["--background-power", "1.2"])
        self.assertAlmostEqual(args.background_power, 1.2, places=6)

    def test_duration_and_dt(self):
        """--duration-ps and --dt-ps correctly set transient parameters."""
        args = self._parse(["--duration-ps", "500.0", "--dt-ps", "2.5"])
        self.assertEqual(args.duration_ps, 500.0)
        self.assertEqual(args.dt_ps, 2.5)

    def test_output_dir_flag(self):
        """--output-dir stores the given path."""
        args = self._parse(["--output-dir", "/tmp/pdn_out"])
        self.assertEqual(args.output_dir, "/tmp/pdn_out")

    def test_no_plots_flag(self):
        """--no-plots sets the flag correctly."""
        args = self._parse(["--no-plots"])
        self.assertTrue(args.no_plots)

    def test_quiet_flag(self):
        """--quiet suppresses verbose output flag."""
        args = self._parse(["--quiet"])
        self.assertTrue(args.quiet)

    def test_combined_flags(self):
        """Multiple flags can be combined."""
        args = self._parse([
            "--chip-size", "300.0",
            "--background-power", "0.5",
            "--no-plots",
            "--quiet",
        ])
        self.assertEqual(args.chip_size, 300.0)
        self.assertAlmostEqual(args.background_power, 0.5)
        self.assertTrue(args.no_plots)
        self.assertTrue(args.quiet)


if __name__ == "__main__":
    unittest.main()
