from pathlib import Path

import pytest

from config import LEAGUE_CONFIG
from pitch_oracle_core.cache import validate_cache


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "precomputed" / "cache_manifest.json"


@pytest.mark.skipif(not MANIFEST.exists(), reason="artifact pipeline has not run yet")
def test_runtime_artifacts_match_core_and_league_contract():
    assert validate_cache(ROOT, expected_league=LEAGUE_CONFIG.key) == ()
