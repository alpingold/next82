"""Collect raw player-season data from nba_api and save to data/raw.

Each dataset is saved as one parquet file per season:
    data/raw/<dataset>/<season>.parquet

Files that already exist are skipped, so the script can be rerun after a failure.

Usage:
    python -m next82.data                    # all seasons in config.SEASONS
    python -m next82.data --seasons 2024-25  # specific seasons
    python -m next82.data --force            # re-download existing files
    python -m next82.data --rosters          # refresh current rosters only
"""
import argparse
import time
from datetime import datetime, timedelta

import pandas as pd
from nba_api.stats.endpoints import (
    commonallplayers,
    leaguedashplayerbiostats,
    leaguedashplayerstats,
    leaguegamelog,
    playergamelogs,
)
from nba_api.stats.static import teams

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


def roster_path(season: str = config.FORECAST_SEASON):
    return config.RAW_DIR / "current_rosters" / f"{season}.parquet"


def fetch_current_rosters(season: str = config.FORECAST_SEASON) -> pd.DataFrame:
    """Every player currently on an NBA roster and their team, saved to data/raw."""
    df = commonallplayers.CommonAllPlayers(
        is_only_current_season=1, season=season, league_id="00", timeout=TIMEOUT
    ).get_data_frames()[0]
    df = df[df.TEAM_ID != 0]
    full_names = {t["id"]: t["full_name"] for t in teams.get_teams()}
    out = pd.DataFrame({
        "PLAYER_ID": df.PERSON_ID,
        "PLAYER_NAME": df.DISPLAY_FIRST_LAST,
        "TEAM_ID": df.TEAM_ID,
        "TEAM_ABBREVIATION": df.TEAM_ABBREVIATION,
        "TEAM_FULL_NAME": df.TEAM_ID.map(full_names),
        "FETCHED_AT": pd.Timestamp.now(),
    })
    path = roster_path(season)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path, index=False)
    return out


def current_rosters(season: str = config.FORECAST_SEASON) -> pd.DataFrame | None:
    """Current rosters, refreshed from nba_api when the saved copy is over a day old.

    Falls back to the saved copy if the API call fails. Returns None if there is
    no saved copy and the API can't be reached.
    """
    path = roster_path(season)
    saved = pd.read_parquet(path) if path.exists() else None
    max_age = timedelta(hours=config.ROSTER_MAX_AGE_HOURS)
    if saved is not None and datetime.now() - saved.FETCHED_AT.iloc[0] < max_age:
        return saved
    try:
        return fetch_current_rosters(season)
    except Exception:
        return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seasons", nargs="+", default=config.SEASONS)
    parser.add_argument("--datasets", nargs="+", default=list(DATASETS), choices=list(DATASETS))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--rosters", action="store_true", help="only refresh current rosters")
    args = parser.parse_args()

    if args.rosters:
        df = fetch_current_rosters()
        print(f"Current rosters ({config.FORECAST_SEASON}): {len(df)} players on {df.TEAM_ID.nunique()} teams")
        return

    for season in args.seasons:
        print(season)
        for dataset in args.datasets:
            if fetch(dataset, season, force=args.force):
                time.sleep(config.REQUEST_DELAY)
    df = fetch_current_rosters()
    print(f"Current rosters ({config.FORECAST_SEASON}): {len(df)} players on {df.TEAM_ID.nunique()} teams")


if __name__ == "__main__":
    main()
