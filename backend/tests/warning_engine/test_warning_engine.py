import unittest

from src.warning_engine import WarningConfig, build_warnings


class WarningEngineTests(unittest.TestCase):
    def setUp(self):
        self.events = {
            "status": "OK",
            "provenance": {"dataset_id": "test"},
            "results": [{
                "event_id": "test:PM25:0001", "start_utc": "2026-10-09T09:00:00+00:00",
                "end_utc": "2026-10-09T09:04:00+00:00", "peak_utc": "2026-10-09T09:01:00+00:00",
                "peak_pm2_5_ug_m3": 80, "peak_baseline_pm2_5_ug_m3": 20,
                "peak_excess_pm2_5_ug_m3": 60, "mean_excess_pm2_5_ug_m3": 35,
                "duration_elapsed_minutes": 4, "coverage_fraction": 1.0,
                "quality_downgraded_candidate_count": 0, "boundary_at_capture_end": False,
            }],
        }

    def test_event_becomes_explainable_elevated_warning(self):
        out = build_warnings(self.events)
        self.assertEqual(out["warning_count"], 1)
        self.assertEqual(out["warnings"][0]["severity"], "ELEVATED")
        self.assertEqual(out["warnings"][0]["status"], "ISSUED")
        self.assertTrue(out["warnings"][0]["reasons"])

    def test_capture_boundary_is_not_claimed_live(self):
        self.events["results"][0]["boundary_at_capture_end"] = True
        out = build_warnings(self.events)
        self.assertEqual(out["warnings"][0]["lifecycle"], "OPEN_AT_CAPTURE_END")
        self.assertTrue(any("live continuation is unknown" in x for x in out["warnings"][0]["reasons"]))

    def test_bad_coverage_degrades_confidence(self):
        self.events["results"][0]["coverage_fraction"] = 0.4
        out = build_warnings(self.events)
        self.assertEqual(out["warnings"][0]["status"], "DEGRADED_CONFIDENCE")

    def test_missing_excess_suppresses_warning(self):
        self.events["results"][0]["peak_excess_pm2_5_ug_m3"] = None
        out = build_warnings(self.events)
        self.assertEqual(out["warnings"][0]["status"], "SUPPRESSED_INSUFFICIENT_EVIDENCE")

    def test_unusable_event_module_does_not_issue(self):
        self.events["status"] = "FAILED_VALIDATION"
        out = build_warnings(self.events)
        self.assertEqual(out["warning_count"], 0)
        self.assertEqual(out["status"], "PARTIAL")

    def test_threshold_validation_is_configurable(self):
        cfg = WarningConfig(watch_excess_ug_m3=10, elevated_excess_ug_m3=20, severe_excess_ug_m3=40)
        out = build_warnings(self.events, config=cfg)
        self.assertEqual(out["warnings"][0]["severity"], "SEVERE")


if __name__ == "__main__":
    unittest.main()