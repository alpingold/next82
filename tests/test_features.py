import pandas as pd
import pytest

from next82.features import FEATURES, OUTPUT_PATH, TARGET, absence_features, load_table, team_schedules


def _schedule(team, n):
    return pd.DataFrame({
        "SEASON": "2024-25",
        "TEAM_ID": team,
        "GAME_ID": [f"{team}-{i:02d}" for i in range(n)],
        "GAME_DATE": [f"2024-11-{i + 1:02d}" for i in range(n)],
    })


def _played(player, team, idxs):
    return pd.DataFrame({
        "SEASON": "2024-25",
        "PLAYER_ID": player,
        "TEAM_ID": team,
        "GAME_ID": [f"{team}-{i:02d}" for i in idxs],
    })


@pytest.fixture
def schedules():
    return team_schedules(pd.concat([_schedule("A", 30), _schedule("B", 30)]))


def test_gap_and_season_end_absence(schedules):
    # Plays games 0-4, misses 5-16 (12 games), plays 17-19, misses 20-29 to end the season.
    games = _played(1, "A", [*range(5), *range(17, 20)])
    row = absence_features(games, schedules).iloc[0]
    assert row.longest_gap == 12
    assert row.missed_start == 0
    assert row.missed_end == 10
    assert row.n_major_gaps == 2


def test_trade_is_not_an_absence(schedules):
    # Plays A games 0-9, then B games 15-29. The switch between teams is not a gap.
    games = pd.concat([_played(2, "A", range(10)), _played(2, "B", range(15, 30))])
    row = absence_features(games, schedules).iloc[0]
    assert row.longest_gap == 0
    assert row.n_teams == 2
    assert row.missed_end == 0


needs_table = pytest.mark.skipif(not OUTPUT_PATH.exists(), reason="feature table not built")


@needs_table
def test_table_shape():
    df = load_table()
    assert not df.duplicated(["PLAYER_ID", "SEASON"]).any()
    assert df.loc[~df.is_forecast, TARGET].notna().all()
    assert df.loc[df.is_forecast, TARGET].isna().all()
    assert set(FEATURES) <= set(df.columns)


@needs_table
def test_full_missed_season_is_zero():
    # Kevin Durant missed all of 2019-20 (Achilles).
    df = load_table()
    row = df[(df.PLAYER_NAME == "Kevin Durant") & (df.SEASON == "2018-19")].iloc[0]
    assert row.gp_next == 0
