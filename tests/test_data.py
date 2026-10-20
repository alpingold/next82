import pytest

from next82 import config
from next82.data import DATASETS, load, raw_path

has_raw = all(raw_path(d, s).exists() for d in DATASETS for s in config.SEASONS)
needs_raw = pytest.mark.skipif(not has_raw, reason="raw data not downloaded")


@needs_raw
def test_game_logs_match_season_totals():
    gp = load("player_stats").groupby("SEASON").GP.sum()
    logs = load("player_games").groupby("SEASON").size()
    assert (gp == logs).all()


@needs_raw
def test_one_row_per_player_season():
    assert not load("player_stats").duplicated(["PLAYER_ID", "SEASON"]).any()


def test_load_missing_season_raises():
    with pytest.raises(FileNotFoundError):
        load("player_stats", ["1900-01"])


def _saved_roster(path, fetched_at):
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "PLAYER_ID": [1], "PLAYER_NAME": ["A"], "TEAM_ID": [10], "TEAM_ABBREVIATION": ["IND"],
        "TEAM_FULL_NAME": ["Indiana Pacers"], "FETCHED_AT": [fetched_at],
    }).to_parquet(path, index=False)


def test_rosters_use_fresh_saved_copy_without_api(tmp_path, monkeypatch):
    import pandas as pd
    from next82 import data

    monkeypatch.setattr(config, "RAW_DIR", tmp_path)
    _saved_roster(data.roster_path(), pd.Timestamp.now())
    monkeypatch.setattr(data, "fetch_current_rosters", lambda season=None: pytest.fail("API should not be called"))
    assert data.current_rosters().TEAM_ABBREVIATION.tolist() == ["IND"]


def test_rosters_fall_back_to_stale_copy_when_api_fails(tmp_path, monkeypatch):
    import pandas as pd
    from next82 import data

    monkeypatch.setattr(config, "RAW_DIR", tmp_path)
    _saved_roster(data.roster_path(), pd.Timestamp.now() - pd.Timedelta(days=3))

    def offline(season=None):
        raise ConnectionError("offline")

    monkeypatch.setattr(data, "fetch_current_rosters", offline)
    assert data.current_rosters().TEAM_ABBREVIATION.tolist() == ["IND"]
