import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from main import app


def recording(frequency=220, amplitude=0.3, seconds=2):
    sr = 22050
    y = amplitude * np.sin(2 * np.pi * frequency * np.arange(int(sr * seconds)) / sr)
    output = io.BytesIO()
    sf.write(output, y, sr, format="WAV", subtype="PCM_16")
    return output.getvalue()


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SMARTKARAOKE_DB": str(Path(self.temp.name) / "test.sqlite3"),
                                          "SMARTKARAOKE_JBL_MODEL": "", "SMARTKARAOKE_ENABLE_MOCK_MODEL": "0"})
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def analyze(self, content, **data):
        return self.client.post("/analyze-audio", files={"file": ("voice.wav", content, "audio/wav")}, data=data)

    def test_real_waveform_features_and_history(self):
        response = self.analyze(recording())
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertFalse(result["is_dummy"])
        self.assertAlmostEqual(result["features"]["pitch_estimate_hz"], 220, delta=10)
        self.assertEqual(len(result["features"]["mfcc_mean"]), 13)
        self.assertEqual(result["room"]["source"], "unknown")
        self.assertEqual(self.client.get("/analyses/" + result["analysis_id"]).json(), result)
        self.assertEqual(self.client.post("/feedback", json={"analysis_id": result["analysis_id"],
                         "device": "JBL K12 Plus", "rating": 4}).status_code, 201)

    def test_spectral_change_changes_eq(self):
        low = self.analyze(recording(120)).json()
        high = self.analyze(recording(6000)).json()
        self.assertLess(low["recommendations"]["Beta Three FX99 Plus"]["eq"]["low_gain_db"], 0)
        self.assertLess(high["recommendations"]["Beta Three FX99 Plus"]["eq"]["high_gain_db"], 0)

    def test_room_measurement_reduces_effects(self):
        dry = self.analyze(recording(), room_rt60_seconds="0.3").json()
        live = self.analyze(recording(), room_rt60_seconds="1.2").json()
        for name in ["Beta Three FX99 Plus"]:
            self.assertLess(live["recommendations"][name]["reverb"]["mix_percent"],
                            dry["recommendations"][name]["reverb"]["mix_percent"])

    def test_jbl_schema_from_audio_and_feedback(self):
        response = self.analyze(recording(), room_rt60_seconds="1.85", vocal_type="male_thick")
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        parameters = result["recommendations"]["JBL K12 Plus"]
        self.assertEqual(parameters["mic_eq"]["bass_pct"], 32)
        self.assertEqual(parameters["echo"]["repeat_pct"], 40)
        self.assertEqual(parameters["reverb"]["mode"], 2)
        payload = {"analysis_id": result["analysis_id"], "device": "JBL K12 Plus", "rating": 4,
                   "expert_parameters": {key: parameters[key] for key in ("mic_eq", "echo", "reverb")}}
        self.assertEqual(self.client.post("/feedback", json=payload).status_code, 201)
        payload["device"] = "Beta Three FX99 Plus"
        self.assertEqual(self.client.post("/feedback", json=payload).status_code, 422)

    def test_reject_bad_uploads(self):
        for content, status in [(b"", 400), (b"not audio", 422),
                                (recording(amplitude=0), 422), (recording(seconds=0.2), 422)]:
            with self.subTest(status=status, length=len(content)):
                self.assertEqual(self.analyze(content).status_code, status)
        self.assertEqual(self.analyze(recording(), room_rt60_seconds="nan").status_code, 422)
        self.assertEqual(self.client.post("/analyze-audio").status_code, 422)
        with patch("main.MAX_UPLOAD_BYTES", 10):
            self.assertEqual(self.analyze(b"x" * 11).status_code, 413)

    def test_invalid_feedback(self):
        self.assertEqual(self.client.post("/feedback", json={"analysis_id": "invalid", "device": "unknown", "rating": 9}).status_code, 422)
        self.assertEqual(self.client.post("/feedback", json={"analysis_id": "00000000-0000-0000-0000-000000000000", "device": "JBL K12 Plus", "rating": 4}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
