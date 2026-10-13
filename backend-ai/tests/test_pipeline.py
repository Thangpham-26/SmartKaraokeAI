import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from schemas import JBLDSPParameters, JBLFeatures
from train_model import train
from utils.jbl_contract import feature_vector, parameters_from_vector


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        generator = runpy.run_path(str(Path(__file__).parents[1] / "data" / "generate_realistic_dataset.py"))
        cls.rows = generator["generate_rows"]()
        cls.dataset = cls.root / "dataset.jsonl"
        cls.dataset.write_text("".join(json.dumps(r) + "\n" for r in cls.rows), encoding="utf-8")
        cls.report = train(cls.dataset, cls.root / "models", allow_mock=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.env = patch.dict(os.environ, {
            "SMARTKARAOKE_DB": str(self.root / "analyses.sqlite3"),
            "SMARTKARAOKE_JBL_MODEL": str(self.root / "models" / "jbl_k12_plus_v2.joblib"),
            "SMARTKARAOKE_ENABLE_MOCK_MODEL": "1",
        })
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def predict(self, row):
        return self.client.post("/predict-dsp", json={"features": row["features"],
                                                     "room_rt60_seconds": row["room_rt60_seconds"]})

    def test_group_split_and_baseline_report(self):
        self.assertEqual(self.report["rows"], 48)
        self.assertEqual(self.report["recording_groups"], 8)
        self.assertEqual((self.report["train_rows"], self.report["test_rows"]), (36, 12))
        self.assertFalse(set(self.report["train_groups"]) & set(self.report["test_groups"]))
        self.assertTrue(self.report["trained_on_mock"])
        self.assertLess(self.report["model_mae_by_parameter"]["repeat_pct"],
                        self.report["baseline_mae_by_parameter"]["repeat_pct"])

    def test_model_prediction_history_and_expert_feedback(self):
        row = self.rows[4]
        response = self.predict(row)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["engine"], "jbl-v2-model")
        recommendation = result["recommendations"]["JBL K12 Plus"]
        self.assertTrue(recommendation["trained_on_mock"])
        self.assertEqual(recommendation["source"], "model")
        self.assertEqual(recommendation["reverb"]["mode"], 2)
        self.assertEqual(self.client.get("/analyses/" + result["analysis_id"]).json(), result)
        response = self.client.post("/feedback", json={"analysis_id": result["analysis_id"],
            "device": "JBL K12 Plus", "rating": 4, "expert_parameters": row["expert_parameters"]})
        self.assertEqual(response.status_code, 201, response.text)

    def test_mock_model_disabled_and_out_of_distribution_fallback(self):
        with patch.dict(os.environ, {"SMARTKARAOKE_ENABLE_MOCK_MODEL": "0"}):
            self.assertFalse(self.client.get("/health").json()["candidate_available"])
            result = self.predict(self.rows[0]).json()
            self.assertEqual(result["recommendations"]["JBL K12 Plus"]["source"], "rules")
        row = {**self.rows[0], "features": {**self.rows[0]["features"], "mfcc_mean": [999.0] * 13}}
        result = self.predict(row).json()
        self.assertEqual(result["engine"], "rules-v2")
        self.assertTrue(any("outside the training" in w for w in result["warnings"]))

    def test_corrupt_candidate_falls_back(self):
        bad = self.root / "broken.joblib"
        bad.write_bytes(b"not a model")
        with patch.dict(os.environ, {"SMARTKARAOKE_JBL_MODEL": str(bad)}):
            response = self.predict(self.rows[0])
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["engine"], "rules-v2")

    def test_contract_rejects_invalid_or_mixed_units(self):
        with self.assertRaises(ValidationError):
            JBLFeatures(mfcc_mean=[0] * 12, pitch_estimate_hz=115)
        with self.assertRaises(ValidationError):
            JBLFeatures(mfcc_mean=[float("nan")] * 13, pitch_estimate_hz=115)
        with self.assertRaises(ValidationError):
            JBLDSPParameters.model_validate({**self.rows[0]["expert_parameters"], "eq": {"low_gain_db": 0}})
        with self.assertRaises(ValidationError):
            JBLDSPParameters.model_validate({**self.rows[0]["expert_parameters"], "reverb": {"level_pct": 25, "mode": 3}})
        with self.assertRaises(ValueError):
            feature_vector(self.rows[0]["features"], None)
        with self.assertRaises(ValueError):
            parameters_from_vector([float("nan")] * 7)

    def test_training_rejects_mock_without_opt_in_and_too_few_groups(self):
        with self.assertRaisesRegex(ValueError, "allow-mock"):
            train(self.dataset, self.root / "rejected")
        few = self.root / "few.jsonl"
        few.write_text("".join(json.dumps(r) + "\n" for r in self.rows[:42]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "8 recording groups"):
            train(few, self.root / "rejected", allow_mock=True)
        self.assertFalse((self.root / "rejected").exists())


if __name__ == "__main__":
    unittest.main()
