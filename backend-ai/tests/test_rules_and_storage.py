import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from storage import get_analysis, save_analysis, save_feedback
from utils.recommendations import recommend


class RuleTests(unittest.TestCase):
    def test_measured_room_and_spectrum_affect_recommendations(self):
        features = {"band_energy_ratio": {"low": 0.6, "mid": 0.3, "high": 0.1},
                    "clipping_fraction": 0, "rms_dbfs": -20}
        dry, _ = recommend(features, 0.3)
        live, _ = recommend(features, 1.2)
        for device in ["Beta Three FX99 Plus"]:
            self.assertEqual(dry[device]["eq"]["low_gain_db"], -2)
            self.assertLess(live[device]["echo"]["mix_percent"], dry[device]["echo"]["mix_percent"])
            self.assertLess(live[device]["reverb"]["mix_percent"], dry[device]["reverb"]["mix_percent"])
            self.assertEqual(live[device]["mapping_status"], "unverified")

    def test_jbl_percentage_rules_and_room_threshold(self):
        features = {"band_energy_ratio": {"low": 0.6, "mid": 0.3, "high": 0.1},
                    "clipping_fraction": 0, "rms_dbfs": -20, "vocal_type": "male_thick"}
        dry, _ = recommend(features, 1.5)
        live, _ = recommend(features, 1.51)
        self.assertEqual(dry["JBL K12 Plus"]["mic_eq"]["bass_pct"], 32)
        self.assertEqual(dry["JBL K12 Plus"]["echo"]["repeat_pct"], 48)
        self.assertEqual(live["JBL K12 Plus"]["echo"]["repeat_pct"], 40)
        self.assertEqual(live["JBL K12 Plus"]["reverb"]["mode"], 2)

    def test_unknown_room_and_clipping_are_reported(self):
        _, warnings = recommend({"band_energy_ratio": {"low": 0.1, "mid": 0.7, "high": 0.2},
                                 "clipping_fraction": 0.02, "rms_dbfs": -40})
        self.assertTrue(any("RT60 is unknown" in w for w in warnings))
        self.assertTrue(any("Clipping" in w for w in warnings))
        self.assertTrue(any("level is low" in w for w in warnings))

    def test_storage_round_trip_and_missing_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"SMARTKARAOKE_DB": str(Path(temp) / "test.sqlite3")}):
                payload = {"analysis_id": "example", "features": {"mfcc_mean": [1.0]}}
                save_analysis(payload)
                self.assertEqual(get_analysis("example"), payload)
                self.assertIsNone(get_analysis("missing"))
                self.assertIsNone(get_analysis("' OR 1=1 --"))
                self.assertTrue(save_feedback({"analysis_id": "example", "rating": 5}))


if __name__ == "__main__":
    unittest.main()
