"""Baseline ("same as last year"), linear regression, and LightGBM models.

All models predict next season's gp_share and are clipped to [0, 1].
"""
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from next82 import config
from next82.features import FEATURES, TARGET


class SameAsLastYear:
    """Predicts that a player plays the same share of games as this season."""

    def fit(self, X: pd.DataFrame, y: pd.Series):
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return X["gp_share"].to_numpy()


class ThreeYearAverage:
    """Predicts the player's average share of games over the last three seasons."""

    def fit(self, X: pd.DataFrame, y: pd.Series):
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return X["avg_gp_share_3yr"].to_numpy()


def linear():
    # Missing history (first seasons in data) is filled with the median and flagged.
    return make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True),
        StandardScaler(),
        Ridge(alpha=1.0),
    )


def lightgbm():
    # L1 objective optimizes MAE directly. Settings chosen on 2022-23 as a
    # validation season, without looking at the test seasons.
    return LGBMRegressor(
        objective="l1",
        n_estimators=300,
        learning_rate=0.02,
        num_leaves=7,
        min_child_samples=80,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=config.RANDOM_STATE,
        verbose=-1,
    )


MODELS = {
    "Same as last year": SameAsLastYear,
    "3-year average": ThreeYearAverage,
    "Linear regression": linear,
    "LightGBM": lightgbm,
}


def fit(name: str, df: pd.DataFrame):
    return MODELS[name]().fit(df[FEATURES], df[TARGET])


def predict(model, df: pd.DataFrame) -> np.ndarray:
    return np.clip(model.predict(df[FEATURES]), 0, 1)
