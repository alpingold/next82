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
