"""Explicitly configured local candidate inference, with rule fallback on failure."""
import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import sklearn

from utils.jbl_contract import (DEVICE, FEATURE_NAMES, SCHEMA_VERSION, TARGET_NAMES,
                                feature_vector, parameters_from_vector)


@lru_cache(maxsize=2)
def load_candidate(path, modified_ns, size):
    # Only load a trusted local artifact explicitly configured by the operator.
    artifact = joblib.load(path)
    if (artifact.get("schema_version") != SCHEMA_VERSION or artifact.get("device") != DEVICE or
            artifact.get("feature_names") != FEATURE_NAMES or artifact.get("target_names") != TARGET_NAMES or
            artifact.get("fixed_reverb_mode") != 2 or
            artifact.get("sklearn_version") != sklearn.__version__ or
            not isinstance(artifact.get("trained_on_mock"), bool)):
        raise ValueError("Candidate contract/version mismatch")
    if not callable(getattr(artifact.get("model"), "predict", None)):
        raise ValueError("Candidate does not support prediction")
    return artifact


def configured_candidate():
    configured_path = os.environ.get("SMARTKARAOKE_JBL_MODEL")
    if not configured_path:
        return None
    path = Path(configured_path).resolve()
    stat = path.stat()
    artifact = load_candidate(str(path), stat.st_mtime_ns, stat.st_size)
    if artifact["trained_on_mock"] and os.environ.get("SMARTKARAOKE_ENABLE_MOCK_MODEL") != "1":
        raise ValueError("Mock candidate is disabled; explicit demo opt-in required")
    return artifact


def model_status():
    try:
        artifact = configured_candidate()
        return {"candidate_configured": bool(os.environ.get("SMARTKARAOKE_JBL_MODEL")),
                "candidate_available": artifact is not None,
                "trained_on_mock": artifact["trained_on_mock"] if artifact else False}
    except Exception:
        return {"candidate_configured": True, "candidate_available": False, "trained_on_mock": False,
                "reason": "Candidate is unavailable, incompatible or not enabled."}


def predict_jbl(features, rt60):
    try:
        artifact = configured_candidate()
        if artifact is None:
            return None, None
        x = np.asarray(feature_vector(features, rt60), dtype=float)
        low = np.asarray(artifact["feature_min"], dtype=float)
        high = np.asarray(artifact["feature_max"], dtype=float)
        if low.shape != x.shape or high.shape != x.shape or not np.isfinite(low).all() or not np.isfinite(high).all() or (low > high).any():
            raise ValueError("Invalid candidate feature envelope")
        # A permissive envelope catches obvious mock/real feature mismatch. It
        # is a fallback guard, not evidence of acoustic calibration or confidence.
        margin = np.maximum((high - low) * 0.1, 0.01)
        if np.any(x < low - margin) or np.any(x > high + margin):
            return None, "JBL model inputs are outside the training feature envelope; rules were used."
        values = artifact["model"].predict(x[None, :])[0]
        result = parameters_from_vector(values)
        result.update(parameter_schema=SCHEMA_VERSION, mapping_status="unverified", source="model",
                      trained_on_mock=artifact["trained_on_mock"],
                      reasons=["JBL v2 candidate prediction from MFCC, pitch and measured RT60.",
                               "Reverb mode remains 2; no other mode was represented in training."])
        warning = "Demo model trained on mock features and rule-generated labels; real acoustic optimization is not validated." if artifact["trained_on_mock"] else "Candidate predictions have not been calibrated to verified device controls."
        return result, warning
    except Exception:
        return None, "JBL candidate unavailable or inputs invalid; rules were used."
