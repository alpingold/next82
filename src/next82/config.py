"""Project-wide paths and settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = ROOT / "models"

# Seasons to collect, in nba_api format ("2015-16").
FIRST_SEASON = 2015
LAST_SEASON = 2025
SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(FIRST_SEASON, LAST_SEASON + 1)]

# Most recent seasons held out for testing (time-based split).
N_TEST_SEASONS = 2

# Seconds between nba_api requests to avoid rate limiting.
REQUEST_DELAY = 0.6

RANDOM_STATE = 42
