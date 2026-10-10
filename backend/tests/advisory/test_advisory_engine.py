import unittest
from src.advisory.config import AdvisoryConfig
from src.advisory.engine import AdvisoryEngine
from src.advisory.rules import select_recommendations
from src.advisory.validator import validate_llm_output

class AdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.warning = {"warning_id":"w1", "event_id":"e1", "status":"ISSUED", "severity":"SEVERE", "pollutant":"PM2.5", "peak_pm2_5_ug_m3":201.5, "peak_baseline_pm2_5_ug_m3":33.9, "peak_excess_pm2_5_ug_m3":167.6, "duration_elapsed_minutes":7, "coverage_fraction":1.0, "lifecycle":"OPEN_AT_CAPTURE_END", "current_gas_readiness":"NOT_READY", "limitations":["Single node"]}

    def test_deterministic_advisory_generates_actions(self):
        result = AdvisoryEngine(AdvisoryConfig()).generate(self.warning)
        self.assertEqual(result["status"], "GENERATED")
        self.assertEqual(result["generation_mode"], "DETERMINISTIC")
        self.assertGreaterEqual(len(result["actions"]), 1)
        self.assertTrue(any("current" in u.lower() for u in result["uncertainty"]))

    def test_capture_boundary_has_current_state_action(self):
        result = select_recommendations({"warning":self.warning})
        self.assertTrue(any(a["action_id"] == "confirm_current_state" for a in result["actions"]))

    def test_gas_not_ready_is_not_called_safe(self):
        result = select_recommendations({"warning":self.warning})
        self.assertTrue(any(a["action_id"] == "note_gas_unavailable" for a in result["actions"]))

    def test_validator_rejects_unapproved_action(self):
        approved = [{"action_id":"a", "title":"A", "instruction":"Do A", "rationale":"Because", "urgency":"ROUTINE", "audience":"SITE_OPERATOR", "evidence_refs":[]}]
        output = {"summary":"s", "reasoning":"r", "language":"en", "action_wording":[{"action_id":"other", "title":"X", "instruction":"x", "rationale":"x"}]}
        with self.assertRaises(ValueError):
            validate_llm_output(output, approved)

    def test_validator_preserves_approved_action_set(self):
        approved = [{"action_id":"a", "title":"A", "instruction":"Do A", "rationale":"Because", "urgency":"ROUTINE", "audience":"SITE_OPERATOR", "evidence_refs":[]}]
        output = {"summary":"s", "reasoning":"r", "language":"en", "action_wording":[{"action_id":"a", "title":"A translated", "instruction":"Do A", "rationale":"Because"}]}
        validated = validate_llm_output(output, approved)
        self.assertEqual(set(validated["actions"]), {"a"})

if __name__ == "__main__":
    unittest.main()