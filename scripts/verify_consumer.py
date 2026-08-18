"""Strict league-neutral artifact and chronological model-quality gate."""

from __future__ import annotations

import json
import math
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import LEAGUE_CONFIG
from pitch_oracle_core import FeatureContract, __version__
from pitch_oracle_core.cache import validate_cache


def production_candidate() -> str:
    """Return the audit-selected production model from the ablation report."""
    report = json.loads(
        (ROOT / "precomputed" / "model-audit" / "model_ablation.json").read_text(encoding="utf-8")
    )
    candidate = report.get("release_gate", {}).get("production_candidate")
    if candidate not in ("no_odds", "poisson"):
        raise SystemExit(f"Model audit did not select a production candidate; got {candidate!r}")
    return candidate


def main() -> None:
    validate_cache(ROOT, expected_league=LEAGUE_CONFIG.key)
    contract = FeatureContract.load(ROOT / "precomputed" / "preprocessed_data.pkl")
    candidate = production_candidate()
    if candidate == "no_odds":
        with (ROOT / "models" / "ensemble_model.pkl").open("rb") as stream:
            ensemble = pickle.load(stream)
        width = getattr(ensemble, "n_features_in_", None)
        if width is not None and width != len(contract.feature_names):
            raise SystemExit(
                f"Ensemble width {width} does not match contract width "
                f"{len(contract.feature_names)}"
            )

    with (ROOT / "models" / "model_performance.pkl").open("rb") as stream:
        performance = pickle.load(stream)
    required = {"class_prior_baseline", "xgb_baseline", "ensemble", "optimized_xgb", "poisson"}
    missing = required.difference(performance)
    if missing:
        raise SystemExit(f"Missing model metrics: {sorted(missing)}")
    for name in ("xgb_baseline", "ensemble", "optimized_xgb"):
        accuracy = float(performance[name]["accuracy"])
        log_loss = float(performance[name]["log_loss"])
        if not (0.0 <= accuracy <= 1.0 and math.isfinite(log_loss) and log_loss < 2.0):
            raise SystemExit(f"Implausible chronological metrics for {name}: {performance[name]}")
    production_name = {"no_odds": "ensemble", "poisson": "poisson"}[candidate]
    production = performance[production_name]
    baseline = performance["class_prior_baseline"]
    if candidate == "poisson":
        production_log_loss = float(production["outcome_log_loss"])
        production_brier = float(production["outcome_brier_score"])
    else:
        production_log_loss = float(production["log_loss"])
        production_brier = float(production["brier_score"])
    if (
        production_log_loss >= float(baseline["log_loss"])
        or production_brier >= float(baseline["brier_score"])
    ):
        raise SystemExit(
            f"Production {production_name} model does not beat the class-prior baseline "
            "on log loss and Brier score"
        )
    poisson_accuracy = float(performance["poisson"]["outcome_acc"])
    if not 0.0 <= poisson_accuracy <= 1.0:
        raise SystemExit(f"Invalid Poisson outcome accuracy: {poisson_accuracy}")

    print(f"{LEAGUE_CONFIG.display_name} artifacts verified with core {__version__}")
    print(f"Feature contract width: {len(contract.feature_names)}")
    print(f"Production model: {production_name}")


if __name__ == "__main__":
    main()
