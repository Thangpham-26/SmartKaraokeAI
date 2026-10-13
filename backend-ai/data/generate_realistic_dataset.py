"""Generate reproducible mock acoustic data with user-specified JBL DSP rules.

Dataset names identify mock scenarios, not actual academic dataset extractions.
The requested expert_verified flag represents mock rule labels, not a real
expert review. Only MFCC coefficients receive small seeded random variations.
"""

import json
import random
from pathlib import Path


VOCAL_MOCKS = [
    {"group": "vocalset_male1", "vocal": "male_thick", "pitch": 115, "mfcc_base": -20.5},
    {"group": "vocalset_male2", "vocal": "male_normal", "pitch": 140, "mfcc_base": -10.0},
    {"group": "vocalset_male3", "vocal": "male_weak", "pitch": 160, "mfcc_base": -5.5},
    {"group": "vocalset_female1", "vocal": "female_high", "pitch": 240, "mfcc_base": 18.2},
    {"group": "vocalset_female2", "vocal": "female_normal", "pitch": 210, "mfcc_base": 12.0},
    {"group": "nus48e_student_m1", "vocal": "male_normal", "pitch": 135, "mfcc_base": -12.4},
    {"group": "nus48e_student_f1", "vocal": "female_weak", "pitch": 195, "mfcc_base": 8.5},
    {"group": "nus48e_student_f2", "vocal": "female_high", "pitch": 235, "mfcc_base": 16.7},
]

ROOM_MOCKS = [
    {"room_id": "openair_studio_booth", "rt60": 0.25},
    {"room_id": "openair_furnished_living_room", "rt60": 0.45},
    {"room_id": "openair_karaoke_vip_treated", "rt60": 0.85},
    {"room_id": "openair_empty_bedroom", "rt60": 1.20},
    {"room_id": "openair_large_garage", "rt60": 1.85},
    {"room_id": "openair_empty_hall", "rt60": 2.50},
]

OUTPUT_PATH = Path(__file__).resolve().parent / "expert_labels_v2.jsonl"


def generate_rows(seed=42):
    """Return 48 rows, preserving eight vocal identities as recording groups."""
    rng = random.Random(seed)
    rows = []
    for vocal in VOCAL_MOCKS:
        for room in ROOM_MOCKS:
            mfcc = [round(vocal["mfcc_base"] + rng.uniform(-0.5, 0.5), 4)
                    for _ in range(13)]
            rows.append({
                "recording_group": vocal["group"],
                "room_id": room["room_id"],
                "features": {
                    "vocal_type": vocal["vocal"],
                    "pitch_estimate_hz": vocal["pitch"],
                    "mfcc_mean": mfcc,
                },
                "room_rt60_seconds": room["rt60"],
                "device": "JBL K12 Plus",
                "expert_verified": True,
                "annotator_id": "tech_jbl_danang_01",
                "expert_parameters": {
                    "mic_eq": {
                        "bass_pct": 32 if vocal["vocal"] == "male_thick" else 38,
                        "mid_pct": 45,
                        "treble_pct": 38,
                    },
                    "echo": {
                        "level_pct": 45,
                        "delay_ms": 210,
                        "repeat_pct": 40 if room["rt60"] > 1.5 else 48,
                    },
                    "reverb": {"level_pct": 25, "mode": 2},
                },
                "provenance": {
                    "is_mock": True,
                    "vocal_source": "VocalSet-inspired mock" if vocal["group"].startswith("vocalset_") else "NUS-48E-inspired mock",
                    "room_source": "OpenAIR-inspired mock",
                    "label_source": "user-specified mock expert rules",
                    "seed": seed,
                },
            })
    if len(rows) != 48 or len({row["recording_group"] for row in rows}) != 8:
        raise ValueError("Expected exactly 48 rows across eight recording groups.")
    return rows


def main():
    rows = generate_rows()
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    print(f"Success: generated {len(rows)} mock rows across 8 recording groups at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
