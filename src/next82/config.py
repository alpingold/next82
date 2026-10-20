"""Project-wide paths and settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = ROOT / "models"

# Seasons to collect, in nba_api format ("2015-16").
FIRST_SEASON = 1996
LAST_SEASON = 2025
SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(FIRST_SEASON, LAST_SEASON + 1)]

# Most recent seasons held out for testing (time-based split).
N_TEST_SEASONS = 2

# Seconds between nba_api requests to avoid rate limiting.
REQUEST_DELAY = 0.6

RANDOM_STATE = 42

# Rotation players: a meaningful role in a season. Used for reporting error and
# for deciding who gets a comeback forecast after sitting out the latest season.
ROTATION_MIN_MPG = 15
ROTATION_MIN_GP_SHARE = 0.25

# A "setback" season: playing fewer than this many games out of 82. Comeback
# forecasts show the chance of a setback plus the expected games if healthy.
SETBACK_GAMES = 20
