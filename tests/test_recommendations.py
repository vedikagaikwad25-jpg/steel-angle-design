import math
import unittest
from dataclasses import replace

from engine import DesignInput, InputError, find_angle
from recommendations import BoltSpec, check_bolts, suggest_sections


class BoltRecommendationTests(unittest.TestCase):
    def setUp(self):
        self.angle = find_angle('ISA 75x75x6')
        self.case = DesignInput(240, 250, 410, 3, 18, 60, 40, 35)
        self.spec = BoltSpec(16, 400, 10, 410)

    def test_known_double_M16_threaded_bolt_shear(self):
        r = check_bolts(self.angle, self.case, True, self.spec)
        area = .78 * math.pi * 16**2 / 4
        predicted = 400 * 2 * area / (math.sqrt(3) * 1.25) / 1000
        self.assertAlmostEqual(r.shear_per_bolt_kn, predicted)
        self.assertEqual(r.shear_planes, 2)
        self.assertAlmostEqual(r.net_thread_area_mm2, area)
        self.assertEqual(r.status, 'Not Satisfy')
        self.assertAlmostEqual(r.kb_angle, 40 / 54)
        self.assertAlmostEqual(r.bearing_gusset_per_bolt_kn,
                               2.5 * (40 / 54) * 16 * 10 * 410 / 1.25 / 1000)

    def test_bolt_count_changes_result(self):
        r = check_bolts(self.angle, replace(self.case, bolts_in_line=5), True, self.spec)
        self.assertEqual(r.status, 'Satisfies')

    def test_single_shear_plane_not_double(self):
        a = check_bolts(self.angle, self.case, False, self.spec)
        b = check_bolts(self.angle, self.case, True, self.spec)
        self.assertAlmostEqual(2 * a.shear_per_bolt_kn, b.shear_per_bolt_kn)

    def test_wrong_hole_diameter_rejected(self):
        with self.assertRaisesRegex(InputError, 'standard hole'):
            check_bolts(self.angle, self.case, False, BoltSpec(20, 400, 10, 410))

    def test_large_grip_rejected(self):
        with self.assertRaisesRegex(InputError, 'Grip exceeds'):
            check_bolts(self.angle, self.case, True, BoltSpec(16, 400, 100, 410))

    def test_search_and_area_filter(self):
        needed, rows = suggest_sections(self.case, True, self.spec)
        self.assertAlmostEqual(needed, 240000 * 1.1 / 250)
        self.assertTrue(rows)
        self.assertTrue(all(r.total_area_mm2 >= needed and r.governing_capacity_kn >= 240 for r in rows))
        self.assertTrue(all(r.bolts >= 2 for r in rows))
        self.assertTrue(all(r.number_of_angles == 2 for r in rows))
        _, none = suggest_sections(self.case, True, self.spec, minimum_area_mm2=9999999)
        self.assertEqual(none, [])


if __name__ == '__main__':
    unittest.main()
