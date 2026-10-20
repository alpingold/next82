from next82 import config


def test_seasons_format():
    assert config.SEASONS[0] == f"{config.FIRST_SEASON}-{str(config.FIRST_SEASON + 1)[-2:]}"
    assert config.SEASONS[-1] == "2025-26"
    assert len(config.SEASONS) == config.LAST_SEASON - config.FIRST_SEASON + 1
