"""Build a consumer's first local artifact cache with the correct league scope."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import LEAGUE_CONFIG  # noqa: E402


def main() -> None:
    load_dotenv(ROOT / ".env", override=False)
    environment = os.environ.copy()
    environment["PITCH_ORACLE_LEAGUE"] = LEAGUE_CONFIG.key
    commands = (
        (sys.executable, "-m", "combine_raw_data"),
        (sys.executable, "-m", "fetch_upcoming_fixtures"),
        (sys.executable, "-m", "prepare_model_data"),
        (
            sys.executable, "-m", "pitch_oracle_core.audit_cli",
            "data_files/combined_historical_data_with_calculations_new.csv",
            "--output-dir", "precomputed/model-audit",
        ),
        (sys.executable, "-m", "train_models"),
        (sys.executable, "-m", "precompute_database"),
        (sys.executable, "scripts/precompute_predictions.py"),
        (sys.executable, "-m", "build_cache_manifest"),
        (sys.executable, "scripts/verify_consumer.py"),
    )
    for command in commands:
        print(f"Running: {' '.join(command)}", flush=True)
        subprocess.run(command, cwd=ROOT, env=environment, check=True)


if __name__ == "__main__":
    main()
