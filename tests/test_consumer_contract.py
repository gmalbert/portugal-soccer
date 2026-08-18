from pathlib import Path

from config import LEAGUE_CONFIG
from pitch_oracle_core import __version__


ROOT = Path(__file__).resolve().parents[1]
CORE_REF = "v1.3.27"


def test_consumer_selects_a_registered_non_epl_league():
    assert LEAGUE_CONFIG.key == "portugal"
    assert LEAGUE_CONFIG.key != "epl"
    assert LEAGUE_CONFIG.football_data_div


def test_core_pin_is_synchronized_everywhere():
    assert __version__ == CORE_REF.removeprefix("v")
    pin = f"pitch-oracle-core[consumer] @ git+https://github.com/gmalbert/pitch-oracle-core.git@{CORE_REF}"
    assert pin in (ROOT / "requirements.txt").read_text()
    assert pin in (ROOT / "requirements-ci.txt").read_text()
    workflow = (ROOT / ".github" / "workflows" / "artifact-pipeline.yml").read_text()
    reusable_workflow = "precompute-consumer.yml@"
    workflow_ref = workflow.split(reusable_workflow, 1)[1].split()[0]
    assert workflow_ref in {CORE_REF, "2907629108d26c436a8b5863f2c067ef6a320bec"}
    assert f"core_ref: {CORE_REF}" in workflow
