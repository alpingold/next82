import numpy as np
import pandas as pd
import pytest

from next82 import evaluate, models
from next82.explain import format_value, top_factors
from next82.features import FEATURES, OUTPUT_PATH, load_table
from next82.train import FORECASTS_PATH


def _rows(n=50, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.random((n, len(FEATURES))), columns=FEATURES)
    df["gp_share_next"] = rng.random(n)
    df["season_games_next"] = 82
    return df


def test_mae_in_games():
    df = pd.DataFrame({"gp_share_next": [0.5, 1.0], "season_games_next": [82, 72]})
    assert evaluate.mae_games(df, np.array([0.0, 1.0])) == pytest.approx(41 / 2)


@pytest.mark.parametrize("name", list(models.MODELS))
def test_models_predict_valid_shares(name):
    df = _rows()
    pred = models.predict(models.fit(name, df), df)
    assert pred.shape == (len(df),)
    assert ((pred >= 0) & (pred <= 1)).all()


def test_baseline_is_same_as_last_year():
    df = _rows()
    pred = models.predict(models.fit("Same as last year", df), df)
    assert np.allclose(pred, df.gp_share.clip(0, 1))


@pytest.mark.skipif(not OUTPUT_PATH.exists(), reason="feature table not built")
def test_split_is_time_ordered():
    train, test = evaluate.split(load_table())
    assert train.season_idx.max() < test.season_idx.min()
    assert not train.is_forecast.any() and not test.is_forecast.any()


def test_format_value():
    assert format_value("gp_share", 0.5) == "41 of 82 games"
    assert format_value("height_in", 83) == "6'11\""
    assert format_value("missed_season_lag1", 1) == "yes"
    assert format_value("age", float("nan")) == "no data"


@pytest.mark.skipif(not FORECASTS_PATH.exists(), reason="forecasts not built")
def test_shap_values_add_up_to_forecast():
    f = pd.read_parquet(FORECASTS_PATH)
    total = f.shap_base + f[[f"shap_{c}" for c in FEATURES]].sum(axis=1)
    assert np.allclose(total, f.pred_games)
    factors = top_factors(f.iloc[0])
    assert len(factors) == 6
    assert factors.impact_games.abs().is_monotonic_decreasing
