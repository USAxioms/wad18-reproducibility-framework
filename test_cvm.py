"""CVM test suite — every scoring rule is pinned and tested."""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from cvm import (value, score_integrity, score_adequacy,
                 score_completeness, score_significance,
                 letter_rating, SCALE)
from manifests import R3_CAPSULE, GPCR_ACE_CAPSULE


class TestIntegrity(unittest.TestCase):

    def test_perfect_integrity(self):
        m = {"chain_integrity": True, "algebraic_exact": True,
             "wad18_thermodynamic_layer": True, "wad18_statically_enforced": True,
             "determinism_contract_declared": True,
             "determinism_tested_byte_identical": True,
             "externally_ratified": True}
        r = score_integrity(m)
        self.assertEqual(r["raw"], 300)

    def test_no_ratification_caps_at_250(self):
        m = {"chain_integrity": True, "algebraic_exact": True,
             "wad18_thermodynamic_layer": True, "wad18_statically_enforced": True,
             "determinism_contract_declared": True,
             "determinism_tested_byte_identical": True,
             "externally_ratified": False}
        r = score_integrity(m)
        self.assertEqual(r["raw"], 250)

    def test_empty_manifest_scores_zero(self):
        r = score_integrity({})
        self.assertEqual(r["raw"], 0)

    def test_penrose_below_threshold(self):
        r = score_integrity({"penrose_residual": 3e-12})
        self.assertEqual(r["sub"]["I2_algebraic_exact"], 50)

    def test_penrose_above_threshold(self):
        r = score_integrity({"penrose_residual": 1e-6})
        self.assertEqual(r["sub"]["I2_algebraic_exact"], 0)


class TestAdequacy(unittest.TestCase):

    def test_100_percent_effective_gives_300(self):
        m = {"mutation_testing": {
            "exhaustive": True, "effective_kill_rate_percent": 100}}
        r = score_adequacy(m)
        self.assertEqual(r["raw"], 300)

    def test_96_percent_gives_288(self):
        m = {"mutation_testing": {
            "exhaustive": True, "effective_kill_rate_percent": 96}}
        r = score_adequacy(m)
        self.assertEqual(r["raw"], 288)

    def test_sampled_halves_rate(self):
        m = {"mutation_testing": {
            "exhaustive": False, "effective_kill_rate_percent": 96}}
        r = score_adequacy(m)
        self.assertEqual(r["raw"], min(300, 48 * 3))

    def test_no_mutation_gives_zero(self):
        r = score_adequacy({})
        self.assertEqual(r["raw"], 0)

    def test_capped_at_300(self):
        m = {"mutation_testing": {
            "exhaustive": True, "effective_kill_rate_percent": 200}}
        r = score_adequacy(m)
        self.assertEqual(r["raw"], 300)


class TestCompleteness(unittest.TestCase):

    def test_all_discharged(self):
        m = {"obligations": {
            "A": {"status": "discharged", "in_scope": True},
            "B": {"status": "discharged", "in_scope": True}}}
        r = score_completeness(m)
        self.assertEqual(r["raw"], 200)

    def test_excluded_not_counted(self):
        m = {"obligations": {
            "A": {"status": "discharged",        "in_scope": True},
            "B": {"status": "excluded",           "in_scope": False},
            "C": {"status": "NOT_DISCHARGED",     "in_scope": True}}}
        r = score_completeness(m)
        self.assertEqual(r["raw"], 100)  # 1/2 × 200

    def test_no_obligations(self):
        r = score_completeness({})
        self.assertEqual(r["raw"], 0)

    def test_discharged_negative_counts(self):
        m = {"obligations": {
            "A": {"status": "discharged_negative", "in_scope": True}}}
        r = score_completeness(m)
        self.assertEqual(r["raw"], 200)


class TestSignificance(unittest.TestCase):

    def test_perfect_significance(self):
        m = {"significance": {
            "falsifiable_predictions": 5,
            "validation_pipeline": {
                "experimental_observable_linked": True,
                "falsification_criterion_stated": True,
                "external_dataset_cited": True},
            "corrections": {"prior_error_corrected": True},
            "novelty": {"novel_contribution_stated": True}}}
        r = score_significance(m)
        self.assertEqual(r["raw"], 200)

    def test_capped_at_5_predictions(self):
        m = {"significance": {"falsifiable_predictions": 10,
             "validation_pipeline": {}, "corrections": {}, "novelty": {}}}
        r = score_significance(m)
        self.assertEqual(r["sub"]["IV1_predictions"], 100)

    def test_zero_significance(self):
        r = score_significance({})
        self.assertEqual(r["raw"], 0)


class TestLetterRating(unittest.TestCase):

    def test_axm(self):
        self.assertEqual(letter_rating(950)["symbol"], "AXM")

    def test_aaa(self):
        self.assertEqual(letter_rating(850)["symbol"], "AAA")

    def test_bbb_is_minimum_ace(self):
        r = letter_rating(500)
        self.assertEqual(r["symbol"], "BBB")
        self.assertIn("ACE minimum", r["label"])

    def test_d_at_zero(self):
        self.assertEqual(letter_rating(0)["symbol"], "D")

    def test_boundary_at_900(self):
        self.assertEqual(letter_rating(900)["symbol"], "AXM")
        self.assertEqual(letter_rating(899)["symbol"], "AAA")


class TestComposite(unittest.TestCase):

    def test_r3_capsule_rating(self):
        result = value(R3_CAPSULE)
        # R3 has: perfect integrity short of ratification (250),
        # 100% effective mutation (300), 7/7 in-scope (200),
        # significance with corrections + novelty + 5 predictions (~160)
        self.assertGreaterEqual(result["CVI_raw"], 800)
        self.assertIn(result["rating"]["symbol"], ("AXM", "AAA"))
        self.assertTrue(result["ace_certified"])

    def test_gpcr_ace_rating(self):
        result = value(GPCR_ACE_CAPSULE)
        # GPCR-ACE: missing mutation (0), 1 undischarged obligation,
        # still gets points for integrity, completeness, significance
        self.assertGreaterEqual(result["CVI_raw"], 400)
        self.assertLess(result["CVI_raw"], 800)

    def test_wad18_values_are_integers(self):
        result = value(R3_CAPSULE)
        for layer in result["layers"].values():
            self.assertIsInstance(layer["wad18"], int)
            self.assertNotIsInstance(layer["wad18"], float)

    def test_cvi_wad_equals_sum_of_layer_wads(self):
        result = value(R3_CAPSULE)
        total  = sum(L["wad18"] for L in result["layers"].values())
        self.assertEqual(result["CVI_wad18"], total)

    def test_empty_manifest_scores_d(self):
        result = value({"name": "empty", "version": "0"})
        self.assertEqual(result["rating"]["symbol"], "D")
        self.assertFalse(result["ace_certified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
