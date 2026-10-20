from next82 import config


def test_seasons_format():
    assert config.SEASONS[0] == "2015-16"
    assert len(config.SEASONS) == config.LAST_SEASON - config.FIRST_SEASON + 1
