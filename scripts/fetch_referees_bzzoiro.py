"""Fetch referee assignments for upcoming Primeira Liga fixtures from Bzzoiro.

Bzzoiro populates the referee field 1-3 days before kickoff.  Run this daily;
when assignments aren't published yet the output file will be empty.

Saves ``data_files/referees.csv`` with columns:
    Date, HomeTeam, AwayTeam, Referee, RefereeID, RefereeCareerGames,
    RefereeCareerYellow, RefereeCareerRed
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

from bzzoiro_football_api import get_events, get_event_detail  # noqa: E402
from team_name_mapping import normalize_team_name  # noqa: E402


def fetch_referees(
    league: str = "portugal",
    days_ahead: int = 14,
    output_dir: Path | str | None = None,
) -> pd.DataFrame:
    today = date.today()
    date_to = (today + timedelta(days=days_ahead)).isoformat()
    aliases = {}
    try:
        from config import LEAGUE_CONFIG
        aliases = LEAGUE_CONFIG.team_aliases or {}
    except Exception:
        pass

    events = get_events(league, date_from=today.isoformat(), date_to=date_to, status="notstarted")
    if not events:
        print(f"No upcoming {league} events from {today} to {date_to}", flush=True)
        _write_empty(output_dir)
        return pd.DataFrame()

    rows = []
    assigned = 0
    for evt in events:
        detail = get_event_detail(evt["id"])
        ref = detail.get("referee")
        if not ref or not ref.get("name"):
            continue
        assigned += 1
        home = normalize_team_name(evt.get("home_team", ""), aliases)
        away = normalize_team_name(evt.get("away_team", ""), aliases)
        match_date = evt.get("event_date", "")[:10]
        rows.append({
            "Date": match_date,
            "HomeTeam": home,
            "AwayTeam": away,
            "Referee": ref.get("name", ""),
            "RefereeID": ref.get("id"),
            "RefereeCareerGames": ref.get("career_games"),
            "RefereeCareerYellow": ref.get("career_yellow_cards"),
            "RefereeCareerRed": ref.get("career_red_cards"),
        })

    result = pd.DataFrame(rows, columns=[
        "Date", "HomeTeam", "AwayTeam", "Referee", "RefereeID",
        "RefereeCareerGames", "RefereeCareerYellow", "RefereeCareerRed",
    ])
    out = Path(output_dir or ROOT / "data_files")
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "referees.csv", index=False)
    print(f"Referees: {assigned}/{len(events)} matches have assignments", flush=True)
    return result


def _write_empty(output_dir: Path | str | None = None) -> None:
    out = Path(output_dir or ROOT / "data_files")
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=[
        "Date", "HomeTeam", "AwayTeam", "Referee", "RefereeID",
        "RefereeCareerGames", "RefereeCareerYellow", "RefereeCareerRed",
    ]).to_csv(out / "referees.csv", index=False)


if __name__ == "__main__":
    fetch_referees()
