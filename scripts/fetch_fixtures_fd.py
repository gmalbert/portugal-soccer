"""Fetch upcoming Primeira Liga fixtures from the football-data.org API.

Portugal has no ESPN slug, so the core fetch_upcoming_fixtures module cannot
be used.  This script hits the football-data.org free-tier REST API (code PPL)
and writes ``data_files/upcoming_fixtures.csv`` in the same five-column format
the rest of the pipeline expects:

    Date, Time, HomeTeam, AwayTeam, Status
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from team_name_mapping import normalize_team_name

ROOT = Path(__file__).resolve().parents[1]

# football-data.org free-tier competition code for Primeira Liga
FD_COMPETITION_CODE = "PPL"

# Status mapping from football-data.org to ESPN-style enum names used by core
_STATUS_MAP = {
    "SCHEDULED": "STATUS_SCHEDULED",
    "TIMED": "STATUS_SCHEDULED",
    "IN_PLAY": "STATUS_IN_PROGRESS",
    "PAUSED": "STATUS_IN_PROGRESS",
    "FINISHED": "STATUS_FULL_TIME",
    "POSTPONED": "STATUS_POSTPONED",
    "CANCELLED": "STATUS_CANCELLED",
    "SUSPENDED": "STATUS_SUSPENDED",
}


def fetch_fixtures(
    api_key: str | None = None,
    output_dir: Path | str | None = None,
    timezone_name: str = "Europe/Lisbon",
    aliases: dict[str, str] | None = None,
) -> pd.DataFrame:
    key = api_key or os.environ.get("FD_API_KEY", "")
    if not key:
        raise RuntimeError("FD_API_KEY is required to fetch fixtures from football-data.org")

    url = f"https://api.football-data.org/v4/competitions/{FD_COMPETITION_CODE}/matches"
    resp = requests.get(url, headers={"X-Auth-Token": key}, timeout=30)
    resp.raise_for_status()

    local_tz = ZoneInfo(timezone_name)
    now = datetime.now(timezone.utc)
    rows = []
    for match in resp.json().get("matches", []):
        utc_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
        if utc_date < now:
            continue
        local = utc_date.astimezone(local_tz)
        status = match.get("status", "SCHEDULED")
        rows.append({
            "Date": local.strftime("%Y-%m-%d"),
            "Time": local.strftime("%H:%M"),
            "HomeTeam": normalize_team_name(match["homeTeam"]["shortName"], aliases),
            "AwayTeam": normalize_team_name(match["awayTeam"]["shortName"], aliases),
            "Status": _STATUS_MAP.get(status, status),
            "kickoff_utc": utc_date.isoformat(),
        })

    result = pd.DataFrame(rows, columns=["Date", "Time", "HomeTeam", "AwayTeam", "Status", "kickoff_utc"])
    out = Path(output_dir or ROOT / "data_files")
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "upcoming_fixtures.csv", index=False)
    print(f"Wrote {len(result)} fixtures to {out / 'upcoming_fixtures.csv'}", flush=True)
    return result


if __name__ == "__main__":
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv
    from config import LEAGUE_CONFIG
    load_dotenv(ROOT / ".env", override=False)
    fetch_fixtures(aliases=LEAGUE_CONFIG.team_aliases)
