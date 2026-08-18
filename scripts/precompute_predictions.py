"""Build the strict upcoming-prediction artifact from the shared feature contract."""

from pathlib import Path
import json
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pitch_oracle_core import (
    FeatureContract,
    add_weather_features,
    build_prediction_frame,
    production_probabilities,
)
from config import LEAGUE_CONFIG  # noqa: E402


def production_candidate() -> str:
    """Return the audit-selected production model from the ablation report."""
    report = json.loads(
        (ROOT / "precomputed" / "model-audit" / "model_ablation.json").read_text(encoding="utf-8")
    )
    candidate = report.get("release_gate", {}).get("production_candidate")
    if candidate not in ("no_odds", "poisson"):
        raise RuntimeError(
            f"Model audit did not select a production candidate; got {candidate!r}"
        )
    return candidate


def generate() -> Path:
    historical = pd.read_csv(
        ROOT / "data_files" / "combined_historical_data_with_calculations_new.csv",
        sep="\t",
    )
    upcoming = pd.read_csv(ROOT / "data_files" / "upcoming_fixtures.csv")
    if LEAGUE_CONFIG.sources.weather and LEAGUE_CONFIG.stadium_coordinates:
        upcoming = add_weather_features(
            upcoming,
            cache_file=f"weather_cache_{LEAGUE_CONFIG.key}.csv",
            stadium_map={team: team for team in LEAGUE_CONFIG.stadium_coordinates},
            stadium_coords={
                team: {"lat": coordinates[0], "lon": coordinates[1]}
                for team, coordinates in LEAGUE_CONFIG.stadium_coordinates.items()
            },
            data_dir=ROOT / "data_files",
            timezone=LEAGUE_CONFIG.sources.weather_timezone,
        )
    contract = FeatureContract.load(ROOT / "precomputed" / "preprocessed_data.pkl")
    candidate = production_candidate()
    probabilities = production_probabilities(
        historical,
        upcoming,
        contract,
        production_candidate=candidate,
        models_dir=ROOT / "models",
    )
    output = ROOT / "data_files" / "upcoming_predictions.csv"
    build_prediction_frame(upcoming, probabilities).to_csv(output, index=False)
    return output


if __name__ == "__main__":
    print(f"Wrote {generate()}")
