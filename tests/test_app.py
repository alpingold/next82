"""App smoke tests. They use only the committed app files, so they run anywhere."""
import pytest

from next82 import config, data
from next82.train import FORECASTS_PATH, HISTORY_PATH, METRICS_PATH, PAST_COMEBACKS_PATH

APP = str(config.ROOT / "app" / "streamlit_app.py")
has_app_files = all(p.exists() for p in [FORECASTS_PATH, HISTORY_PATH, PAST_COMEBACKS_PATH, METRICS_PATH])
pytestmark = pytest.mark.skipif(not has_app_files, reason="app data files not built")


@pytest.fixture
def app(monkeypatch):
    from streamlit.testing.v1 import AppTest

    # Never call nba_api from tests: a stale roster refresh would otherwise start.
    def offline(season=None):
        raise ConnectionError("no network in tests")

    monkeypatch.setattr(data, "fetch_current_rosters", offline)
    return AppTest.from_file(APP, default_timeout=60).run()


def _pick(at, text):
    box = at.selectbox(key="player_label")
    box.select(next(o for o in box.options if text in o)).run()


def test_home_page_lists_forecasts(app):
    assert not app.exception
    assert app.dataframe and len(app.dataframe[0].value) > 300


def test_player_page_and_back(app):
    _pick(app, "Joel Embiid")
    assert not app.exception
    assert app.subheader[0].value.startswith("Joel Embiid")
    app.button[0].click().run()
    assert app.selectbox(key="player_label").value is None


def test_comeback_player_shows_two_part_forecast(app):
    _pick(app, "Tyrese Haliburton")
    labels = [m.label for m in app.metric]
    assert any("if healthy" in label for label in labels)
    assert "Chance of a setback" in labels


def test_accent_free_search_label(app):
    options = app.selectbox(key="player_label").options
    assert any("Jokić (Jokic)" in o for o in options)


def test_team_filter_limits_players(app):
    team_box = app.selectbox[0]
    if len(team_box.options) == 1:
        pytest.skip("rosters not downloaded")
    team_box.select("Indiana Pacers").run()
    assert not app.exception
    assert all(o.endswith("· IND") for o in app.selectbox(key="player_label").options)
