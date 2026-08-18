"""League-owned configuration for a thin Pitch Oracle consumer."""

from pitch_oracle_core import get_league_config


# Replace with any key in pitch_oracle_core.BUILTIN_LEAGUES.
LEAGUE_CONFIG = get_league_config("portugal")
