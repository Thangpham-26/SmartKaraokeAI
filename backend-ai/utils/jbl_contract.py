"""Shared, finite training/inference vectors for the user-specified JBL v2 schema."""
import math

from schemas import JBLDSPParameters, JBLFeatures

SCHEMA_VERSION = "jbl-v2"
DEVICE = "JBL K12 Plus"
FEATURE_NAMES = [f"mfcc_mean_{i}" for i in range(13)] + ["pitch_estimate_hz", "rt60_seconds"]
TARGET_NAMES = ["bass_pct", "mid_pct", "treble_pct", "echo_level_pct", "delay_ms", "repeat_pct", "reverb_level_pct"]


def feature_vector(features, rt60):
    # API features include additional diagnostics, which are not model inputs.
    subset = {key: features[key] for key in ("mfcc_mean", "pitch_estimate_hz") if key in features}
    validated = JBLFeatures.model_validate(subset)
    if rt60 is None or not math.isfinite(float(rt60)) or not 0.1 <= float(rt60) <= 5:
        raise ValueError("Measured RT60 must be finite and between 0.1 and 5 seconds")
    return validated.mfcc_mean + [validated.pitch_estimate_hz, float(rt60)]


def target_vector(parameters):
    p = JBLDSPParameters.model_validate(parameters)
    return [p.mic_eq.bass_pct, p.mic_eq.mid_pct, p.mic_eq.treble_pct,
            p.echo.level_pct, p.echo.delay_ms, p.echo.repeat_pct, p.reverb.level_pct]


def parameters_from_vector(values):
    values = [float(v) for v in values]
    if len(values) != len(TARGET_NAMES) or not all(math.isfinite(v) for v in values):
        raise ValueError("Invalid model prediction")
    def pct(index):
        return round(max(0.0, min(100.0, values[index])), 2)
    return JBLDSPParameters.model_validate({
        "mic_eq": {"bass_pct": pct(0), "mid_pct": pct(1), "treble_pct": pct(2)},
        "echo": {"level_pct": pct(3), "delay_ms": max(80, min(250, round(values[4]))), "repeat_pct": pct(5)},
        "reverb": {"level_pct": pct(6), "mode": 2},
    }).model_dump()
