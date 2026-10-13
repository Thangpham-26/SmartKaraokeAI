"""User-specified JBL percentages and experimental generic Beta Three rules."""
DEVICE_PROFILES = {
    name: {"mapping_status": "unverified", "manual_source": None,
           "parameter_space": "generic DSP units; verify against device manual"}
    for name in ("JBL K12 Plus", "Beta Three FX99 Plus")
}
DEVICE_PROFILES["JBL K12 Plus"].update(
    parameter_schema="jbl-v2", parameter_space="user-specified percentages and mode; vendor mapping unverified")
DEVICE_PROFILES["Beta Three FX99 Plus"]["parameter_schema"] = "generic-v1"


def jbl_rules(features, room_rt60_seconds=None):
    vocal_type = features.get("vocal_type")
    return {
        "mic_eq": {"bass_pct": 32 if vocal_type == "male_thick" else 38,
                   "mid_pct": 45, "treble_pct": 38},
        "echo": {"level_pct": 45, "delay_ms": 210,
                 "repeat_pct": 40 if room_rt60_seconds is not None and room_rt60_seconds > 1.5 else 48},
        "reverb": {"level_pct": 25, "mode": 2},
        "parameter_schema": "jbl-v2", "source": "rules", "trained_on_mock": False,
        "mapping_status": "unverified",
        "reasons": ["User-specified JBL rules; bass is 32% for male_thick, otherwise 38%.",
                    "Repeat is 40% when measured RT60 exceeds 1.5 s, otherwise 48%.",
                    "Vocal type is user-supplied, not classified automatically."],
    }


def recommend(features, room_rt60_seconds=None):
    bands = features["band_energy_ratio"]
    eq = {"low_gain_db": -2.0 if bands["low"] > 0.35 else 0.0,
          "mid_gain_db": -1.0 if bands["mid"] > 0.85 else 0.0,
          "high_gain_db": -1.5 if bands["high"] > 0.2 else 0.0}
    reasons = ["EQ cuts follow measured spectral energy; no boost is applied."]
    echo = {"delay_ms": 160, "feedback_percent": 15, "mix_percent": 10}
    reverb = {"decay_seconds": 1.2, "mix_percent": 12}
    warnings = ["Experimental recommendations; optimal acoustic settings have not been validated.",
                "Device control ranges and mappings have not been verified.",
                "Pitch is a rough estimate for solo vocals; backing music affects these features."]
    if room_rt60_seconds is None:
        warnings.append("Room RT60 is unknown. It is not inferred from vocal audio.")
    elif room_rt60_seconds > 0.8:
        echo.update(feedback_percent=8, mix_percent=5)
        reverb.update(decay_seconds=0.6, mix_percent=5)
        reasons.append("Measured room RT60 exceeds 0.8 s; reduce added echo and reverb.")
    else:
        reasons.append("Measured room RT60 is at most 0.8 s; use modest effects.")
    if features["clipping_fraction"] > 0.001:
        warnings.append("Clipping detected. Lower recording input gain and record again.")
    if features["rms_dbfs"] < -35:
        warnings.append("Recording level is low; background noise may affect the analysis.")
    if not features.get("vocal_type"):
        warnings.append("Vocal type is unknown; JBL rule fallback uses 38% bass.")
    return {
        "JBL K12 Plus": jbl_rules(features, room_rt60_seconds),
        "Beta Three FX99 Plus": {"eq": eq, "echo": echo, "reverb": reverb,
                                 "parameter_schema": "generic-v1", "source": "rules",
                                 "trained_on_mock": False, "mapping_status": "unverified", "reasons": reasons},
    }, warnings
