"""Exercise generation, training, candidate inference, audio upload and feedback."""
import io
import json
import math
import os
import runpy
import struct
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from train_model import train

ROOT = Path(__file__).resolve().parent


def waveform():
    """Two-second synthetic WAV for an actual decoder/feature/API smoke check."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22050)
        samples = [round(10000 * math.sin(2 * math.pi * 115 * i / 22050)) for i in range(44100)]
        output.writeframes(struct.pack("<" + "h" * len(samples), *samples))
    return buffer.getvalue()


def main():
    generator = runpy.run_path(str(ROOT / "data" / "generate_realistic_dataset.py"))
    generator["main"]()
    dataset = ROOT / "data" / "expert_labels_v2.jsonl"
    destination = ROOT / "models" / "demo"
    evaluation = train(dataset, destination, allow_mock=True)
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    with tempfile.TemporaryDirectory(prefix="smartkaraoke-demo-") as temp:
        with patch.dict(os.environ, {"SMARTKARAOKE_JBL_MODEL": str(destination / "jbl_k12_plus_v2.joblib"),
                                    "SMARTKARAOKE_ENABLE_MOCK_MODEL": "1",
                                    "SMARTKARAOKE_DB": str(Path(temp) / "demo.sqlite3")}):
            with TestClient(app) as client:
                status = client.get("/health").json()
                if not status["candidate_available"]:
                    raise RuntimeError("Candidate did not load")
                sources = []
                for row in rows:
                    response = client.post("/predict-dsp", json={"features": row["features"],
                                                                "room_rt60_seconds": row["room_rt60_seconds"]})
                    response.raise_for_status()
                    result = response.json()
                    source = result["recommendations"]["JBL K12 Plus"]["source"]
                    if source != "model":
                        raise RuntimeError("In-domain mock features did not reach candidate inference")
                    sources.append(source)
                stored = client.get("/analyses/" + result["analysis_id"])
                stored.raise_for_status()
                if stored.json() != result:
                    raise RuntimeError("History mismatch")
                feedback = client.post("/feedback", json={"analysis_id": result["analysis_id"],
                    "device": "JBL K12 Plus", "rating": 4, "notes": "Synthetic pipeline smoke test",
                    "expert_parameters": rows[-1]["expert_parameters"]})
                feedback.raise_for_status()
                audio = client.post("/analyze-audio", files={"file": ("smoke.wav", waveform(), "audio/wav")},
                                    data={"room_rt60_seconds": "1.85", "vocal_type": "male_thick"})
                audio.raise_for_status()
                audio_result = audio.json()
                if audio_result["recommendations"]["JBL K12 Plus"]["source"] != "rules":
                    raise RuntimeError("Expected rule fallback for real extracted features outside the mock envelope")
                report = {
                    "status": "passed", "transport": "FastAPI TestClient",
                    "dataset_rows": len(rows), "recording_groups": evaluation["recording_groups"],
                    "train_rows": evaluation["train_rows"], "test_rows": evaluation["test_rows"],
                    "group_overlap": evaluation["group_overlap"], "mock_predictions": len(sources),
                    "history_status": stored.status_code, "feedback_status": feedback.status_code,
                    "audio_upload_status": audio.status_code,
                    "audio_source": audio_result["recommendations"]["JBL K12 Plus"]["source"],
                    "audio_mfcc_count": len(audio_result["features"]["mfcc_mean"]),
                    "audio_warning": audio_result["warnings"],
                    "trained_on_mock": True,
                    "limitations": "Synthetic rule/data pipeline validation only; not acoustic optimization or Android device testing.",
                }
    (destination / "smoke-report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
