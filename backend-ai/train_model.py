"""Train a JBL v2 candidate with a group-disjoint evaluation and explicit mock opt-in."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupShuffleSplit

from utils.jbl_contract import (DEVICE, FEATURE_NAMES, SCHEMA_VERSION, TARGET_NAMES,
                                feature_vector, target_vector)


def train(dataset, output, allow_mock=False):
    dataset = Path(dataset)
    output = Path(output)
    rows = []
    for line_number, line in enumerate(dataset.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if (row.get("device") != DEVICE or row.get("expert_verified") is not True or
                    not isinstance(row.get("annotator_id"), str) or not row["annotator_id"].strip() or
                    not isinstance(row.get("recording_group"), str) or not row["recording_group"].strip()):
                raise ValueError("Need JBL K12 Plus, expert_verified=true, annotator_id and recording_group")
            feature_vector(row["features"], row["room_rt60_seconds"])
            target_vector(row["expert_parameters"])
            # Unspecified provenance is not treated as verified real data.
            is_mock = row.get("provenance", {}).get("is_mock")
            if not isinstance(is_mock, bool):
                raise ValueError("Need explicit provenance.is_mock=true or false")
            if is_mock and not allow_mock:
                raise ValueError("Mock data requires --allow-mock and produces a demo candidate only")
            rows.append(row)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"Line {line_number}: {exc}") from exc
    groups = [r["recording_group"] for r in rows]
    if len(rows) < 40 or len(set(groups)) < 8:
        raise ValueError("Need at least 40 rows across 8 recording groups")
    x = np.asarray([feature_vector(r["features"], r["room_rt60_seconds"]) for r in rows])
    y = np.asarray([target_vector(r["expert_parameters"]) for r in rows])
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42).split(x, y, groups))
    train_groups = sorted({groups[i] for i in train_idx})
    test_groups = sorted({groups[i] for i in test_idx})
    if set(train_groups) & set(test_groups):
        raise ValueError("Recording group leakage detected")
    model = RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=1)
    model.fit(x[train_idx], y[train_idx])
    prediction = model.predict(x[test_idx])
    baseline = np.repeat(y[train_idx].mean(axis=0)[None, :], len(test_idx), axis=0)
    trained_on_mock = any(r["provenance"]["is_mock"] for r in rows)
    report = {
        "device": DEVICE, "schema_version": SCHEMA_VERSION,
        "trained_on_mock": trained_on_mock,
        "evaluation_scope": "synthetic rule reproduction only" if trained_on_mock else "held-out recording groups; hardware calibration still unverified",
        "rows": len(rows), "recording_groups": len(set(groups)),
        "train_rows": len(train_idx), "test_rows": len(test_idx),
        "train_groups": train_groups, "test_groups": test_groups, "group_overlap": [],
        "feature_names": FEATURE_NAMES, "target_names": TARGET_NAMES,
        "model_mae_by_parameter": dict(zip(TARGET_NAMES, mean_absolute_error(y[test_idx], prediction, multioutput="raw_values").tolist())),
        "baseline_mae_by_parameter": dict(zip(TARGET_NAMES, mean_absolute_error(y[test_idx], baseline, multioutput="raw_values").tolist())),
        "fixed_reverb_mode": 2,
        "mode_note": "Mode 2 is the only supported categorical value; it is not regressed.",
        "mapping_status": "unverified",
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "sklearn_version": sklearn.__version__,
    }
    # Evaluation above uses held-out groups. Refit the saved candidate on all rows.
    model.fit(x, y)
    artifact = {
        "model": model, "device": DEVICE, "schema_version": SCHEMA_VERSION,
        "feature_names": FEATURE_NAMES, "target_names": TARGET_NAMES,
        "trained_on_mock": trained_on_mock, "mapping_status": "unverified",
        "fixed_reverb_mode": 2, "sklearn_version": sklearn.__version__,
        "feature_min": x.min(axis=0).tolist(), "feature_max": x.max(axis=0).tolist(),
        "evaluation": report,
    }
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output / "jbl_k12_plus_v2.joblib")
    (output / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "models")
    parser.add_argument("--allow-mock", action="store_true", help="Explicitly permit synthetic demo data")
    args = parser.parse_args()
    print(json.dumps(train(args.dataset, args.output, args.allow_mock), indent=2))
