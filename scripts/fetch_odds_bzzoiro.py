"""Fetch pre-match odds for upcoming Primeira Liga fixtures from Bzzoiro.

Saves ``data_files/odds.csv`` with columns the best-bets exporter expects:
HomeTeam, AwayTeam, Date, OddsHome, OddsDraw, OddsAway.

Run once per day before the prediction pipeline.  The Bzzoiro API is free,
unlimited, and has no rate limits.
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env", override=False)

from bzzoiro_football_api import get_events, get_event_detail, normalize_bzzoiro_team  # noqa: E402


def fetch_odds(
    league: str = "portugal",
    days_ahead: int = 7,
    output_dir: Path | str | None = None,
) -> pd.DataFrame:
    today = date.today()
    date_to = (today + timedelta(days=days_ahead)).isoformat()

    events = get_events(league, date_from=today.isoformat(), date_to=date_to, status="notstarted")
    if not events:
        print(f"No upcoming {league} events found from {today} to {date_to}", flush=True)
        out = Path(output_dir or ROOT / "data_files")
        out.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=["HomeTeam", "AwayTeam", "Date", "OddsHome", "OddsDraw", "OddsAway"]).to_csv(
            out / "odds.csv", index=False
        )
        return pd.DataFrame()

    rows = []
    for evt in events:
        event_id = evt["id"]
        detail = get_event_detail(event_id)
        home = normalize_bzzoiro_team(evt.get("home_team", ""))
        away = normalize_bzzoiro_team(evt.get("away_team", ""))
        match_date = evt.get("event_date", "")[:10]
        odds_h = detail.get("odds_home")
        odds_d = detail.get("odds_draw")
        odds_a = detail.get("odds_away")
        if odds_h and odds_d and odds_a:
            rows.append({
                "HomeTeam": home,
                "AwayTeam": away,
                "Date": match_date,
                "OddsHome": odds_h,
                "OddsDraw": odds_d,
                "OddsAway": odds_a,
            })

    result = pd.DataFrame(rows, columns=["HomeTeam", "AwayTeam", "Date", "OddsHome", "OddsDraw", "OddsAway"])
    out = Path(output_dir or ROOT / "data_files")
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "odds.csv", index=False)
    print(f"Wrote {len(result)} odds rows to {out / 'odds.csv'}", flush=True)
    return result


if __name__ == "__main__":
    fetch_odds()
