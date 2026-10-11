import csv, io, os, subprocess, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fba_triage as ft

class T(unittest.TestCase):
    def test_small_standard(self):
        tier, fee = ft.fba_fee(ft.DEFAULT_FEES, 0.3, [8, 5, 0.5])
        self.assertEqual(tier, "small_standard"); self.assertAlmostEqual(fee, 3.15)
    def test_referral_min(self):
        self.assertAlmostEqual(ft.referral(ft.DEFAULT_FEES, 1.0, "toys"), 0.30)
    def test_verdicts(self):
        row = dict(sale_price="19.99", unit_cost="4.10", weight_lb="0.6", length_in="16.5",
                   width_in="3", height_in="3", category="kitchen", competitors="8")
        self.assertEqual(ft.score(row, ft.DEFAULT_FEES, 30, 3)["verdict"], "BUY")
        row.update(unit_cost="15")
        self.assertEqual(ft.score(row, ft.DEFAULT_FEES, 30, 3)["verdict"], "PASS")
    def test_cli_missing_file(self):
        r = subprocess.run([sys.executable, "fba_triage.py", "nope.csv"], capture_output=True, text=True,
                           cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assertEqual(r.returncode, 1)

if __name__ == "__main__":
    unittest.main()
