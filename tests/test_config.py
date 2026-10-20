from datetime import date

from next82 import config


def test_seasons_format():
    assert config.SEASONS[0] == f"{config.FIRST_SEASON}-{str(config.FIRST_SEASON + 1)[-2:]}"
    assert config.SEASONS[-1] == f"{config.LAST_SEASON}-{str(config.LAST_SEASON + 1)[-2:]}"
    assert len(config.SEASONS) == config.LAST_SEASON - config.FIRST_SEASON + 1
    assert config.FORECAST_SEASON == f"{config.LAST_SEASON + 1}-{str(config.LAST_SEASON + 2)[-2:]}"


def test_last_completed_season_moves_forward_in_may():
    assert config.last_completed_season(date(2026, 10, 19)) == 2025
    assert config.last_completed_season(date(2027, 4, 30)) == 2025
    assert config.last_completed_season(date(2027, 5, 1)) == 2026
