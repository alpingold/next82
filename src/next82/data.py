"""Collect raw player-season data from nba_api and save to data/raw.

Each dataset is saved as one parquet file per season:
    data/raw/<dataset>/<season>.parquet

Files that already exist are skipped, so the script can be rerun after a failure.

Usage:
    python -m next82.data                    # all seasons in config.SEASONS
    python -m next82.data --seasons 2024-25  # specific seasons
    python -m next82.data --force            # re-download existing files
"""
import argparse
import time

import pandas as pd
from nba_api.stats.endpoints import (
    leaguedashplayerbiostats,
    leaguedashplayerstats,
    leaguegamelog,
    playergamelogs,
)

from next82 import config

SEASON_TYPE = "Regular Season"
TIMEOUT = 60
MAX_RETRIES = 4


def _player_stats(season: str) -> pd.DataFrame:
    """Season totals per player: age, games played, minutes, box score stats."""
    return leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star=SEASON_TYPE,
        per_mode_detailed="Totals",
        timeout=TIMEOUT,
    ).get_data_frames()[0]


def _player_bio(season: str) -> pd.DataFrame:
    """Height, weight, draft year and country per player."""
    return leaguedashplayerbiostats.LeagueDashPlayerBioStats(
        season=season,
        season_type_all_star=SEASON_TYPE,
        timeout=TIMEOUT,
    ).get_data_frames()[0]


def _player_games(season: str) -> pd.DataFrame:
    """One row per player per game played. Used to find stretches of missed games."""
    return playergamelogs.PlayerGameLogs(
        season_nullable=season,
        season_type_nullable=SEASON_TYPE,
        timeout=TIMEOUT,
    ).get_data_frames()[0]


def _team_games(season: str) -> pd.DataFrame:
    """One row per team per game. Gives each team's full schedule."""
    return leaguegamelog.LeagueGameLog(
        season=season,
        season_type_all_star=SEASON_TYPE,
        player_or_team_abbreviation="T",
        timeout=TIMEOUT,
    ).get_data_frames()[0]


DATASETS = {
    "player_stats": _player_stats,
    "player_bio": _player_bio,
    "player_games": _player_games,
    "team_games": _team_games,
}


def raw_path(dataset: str, season: str):
    return config.RAW_DIR / dataset / f"{season}.parquet"


def fetch(dataset: str, season: str, force: bool = False) -> bool:
    """Download one dataset for one season. Returns True if a request was made."""
    path = raw_path(dataset, season)
    if path.exists() and not force:
        return False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            df = DATASETS[dataset](season)
            break
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            wait = 5 * attempt
            print(f"  {dataset} {season}: {type(e).__name__}, retrying in {wait}s")
            time.sleep(wait)

    df["SEASON"] = season
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    print(f"  {dataset} {season}: {len(df):,} rows")
    return True


def load(dataset: str, seasons: list[str] | None = None) -> pd.DataFrame:
    """Load a raw dataset across seasons into one DataFrame."""
    seasons = seasons or config.SEASONS
    paths = [raw_path(dataset, s) for s in seasons]
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing raw files, run `python -m next82.data`: {missing}")
    return pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seasons", nargs="+", default=config.SEASONS)
    parser.add_argument("--datasets", nargs="+", default=list(DATASETS), choices=list(DATASETS))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    for season in args.seasons:
        print(season)
        for dataset in args.datasets:
            if fetch(dataset, season, force=args.force):
                time.sleep(config.REQUEST_DELAY)


if __name__ == "__main__":
    main()
