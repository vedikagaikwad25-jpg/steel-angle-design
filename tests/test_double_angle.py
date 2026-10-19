"""Independent expected values and symmetry/invalid-input checks."""
import unittest

from engine import DesignInput, InputError, calculate_tension, find_angle
from double_angle import calculate_double_tension


class DoubleAngleTests(unittest.TestCase):
    def setUp(self):
        self.angle = find_angle("ISA 75x75x6")
        self.inp = DesignInput(240, 250, 410, 3, 18, 60, 40, 35)

    def test_total_strengths_match_independent_known_case(self):
        r = calculate_double_tension(self.angle, self.inp)
        self.assertAlmostEqual(r.gross_yield_kn, 2 * 198.86363636, places=5)
        self.assertAlmostEqual(r.net_rupture_kn, 2 * 183.80887982, places=5)
        self.assertAlmostEqual(r.block_shear_kn, 2 * 172.14477618, places=5)
        self.assertAlmostEqual(r.design_strength_kn, 344.28955236, places=5)
        self.assertTrue(r.overall_pass)
        self.assertEqual(r.per_angle.inputs.force_kn, 120)
        self.assertEqual(r.inputs.force_kn, 240)

    def test_each_per_angle_result_is_unchanged(self):
        r = calculate_double_tension(self.angle, self.inp)
        original = calculate_tension(self.angle, self.inp)
        self.assertAlmostEqual(r.gross_yield_kn, 2 * original.gross_yield_kn)
        self.assertAlmostEqual(r.beta_used, original.beta_used)
        self.assertAlmostEqual(r.bs_mm, original.bs_mm)
        self.assertAlmostEqual(r.avg_mm2, 2 * original.avg_mm2)
        self.assertAlmostEqual(r.connected_net_area_mm2, 2 * original.connected_net_area_mm2)

    def test_total_member_failure(self):
        from dataclasses import replace
        r = calculate_double_tension(self.angle, replace(self.inp, force_kn=360))
        self.assertFalse(r.overall_pass)
        self.assertFalse(r.check(r.block_shear_kn))
        self.assertTrue(r.check(r.gross_yield_kn))

    def test_invalid_hole_layout_rejected(self):
        from dataclasses import replace
        with self.assertRaises(InputError):
            calculate_double_tension(self.angle, replace(self.inp, gauge_mm=73))

    def test_zero_force_rejected(self):
        from dataclasses import replace
        with self.assertRaises(InputError):
            calculate_double_tension(self.angle, replace(self.inp, force_kn=0))


if __name__ == '__main__':
    unittest.main()
