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
    upcoming = _add_goal_averages(historical, upcoming)
    contract = FeatureContract.load(ROOT / "precomputed" / "preprocessed_data.pkl")
    candidate = production_candidate()
    probabilities = production_probabilities(
        historical,
        upcoming,
        contract,
        production_candidate=candidate,
        models_dir=ROOT / "models",
    )
    predictions = build_prediction_frame(upcoming, probabilities)
    output = ROOT / "data_files" / "upcoming_predictions.csv"
    predictions = _merge_odds_and_recommend(predictions)
    predictions.to_csv(output, index=False)
    return output


def _add_goal_averages(historical: pd.DataFrame, upcoming: pd.DataFrame) -> pd.DataFrame:
    """Add HomeGoalsAve/AwayGoalsAve from recent history for each team."""
    date_col = "MatchDate" if "MatchDate" in historical.columns else "Date"
    home_avgs = (
        historical.sort_values(date_col)
        .groupby("HomeTeam")[["HomeGoalsAve"]]
        .last()
        .rename(columns={"HomeGoalsAve": "HomeGoalsAve_lookup"})
    )
    away_avgs = (
        historical.sort_values(date_col)
        .groupby("AwayTeam")[["AwayGoalsAve"]]
        .last()
        .rename(columns={"AwayGoalsAve": "AwayGoalsAve_lookup"})
    )
    upcoming = upcoming.merge(home_avgs, left_on="HomeTeam", right_index=True, how="left")
    upcoming = upcoming.merge(away_avgs, left_on="AwayTeam", right_index=True, how="left")
    upcoming["HomeGoalsAve"] = upcoming["HomeGoalsAve_lookup"]
    upcoming["AwayGoalsAve"] = upcoming["AwayGoalsAve_lookup"]
    upcoming.drop(columns=["HomeGoalsAve_lookup", "AwayGoalsAve_lookup"], inplace=True)
    return upcoming


def _merge_odds_and_recommend(predictions: pd.DataFrame) -> pd.DataFrame:
    """Merge Bzzoiro odds and compute bet recommendations."""
    from pitch_oracle_core.best_bets import market_metrics

    odds_path = ROOT / "data_files" / "odds.csv"
    if not odds_path.exists():
        return predictions

    odds = pd.read_csv(odds_path)
    if odds.empty:
        return predictions

    merge_cols = ["HomeTeam", "AwayTeam", "Date"]
    predictions = predictions.merge(odds, on=merge_cols, how="left", suffixes=("", "_odds"))

    MIN_EDGE = 0.03
    MIN_EV = 0.03

    outcomes = [
        ("HomeWin_Prob", "OddsHome", "Home Win"),
        ("Draw_Prob", "OddsDraw", "Draw"),
        ("AwayWin_Prob", "OddsAway", "Away Win"),
    ]

    for idx, row in predictions.iterrows():
        probs = [_safe_float(row.get(c)) for c, _, _ in outcomes]
        odds_vals = [_safe_float(row.get(c)) for _, c, _ in outcomes]
        if any(p is None for p in probs) or any(o is None or o <= 1 for o in odds_vals):
            continue
        total = sum(probs)
        if total <= 0:
            continue
        probs = [p / total for p in probs]

        best_edge = 0
        best_outcome = ""
        best_ev = 0
        for prob, odds_val, label in zip(probs, odds_vals, outcomes):
            _, edge, ev = market_metrics(prob, odds_val, odds_vals)
            if edge > best_edge:
                best_edge = edge
                best_outcome = label[2]
                best_ev = ev

        if best_edge >= MIN_EDGE and best_ev >= MIN_EV:
            predictions.at[idx, "BetRecommendation"] = f"Bet {best_outcome}"
            predictions.at[idx, "BetReason"] = (
                f"{best_edge:.1%} edge over market, {best_ev:.1%} expected value"
            )

    return predictions


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    print(f"Wrote {generate()}")
