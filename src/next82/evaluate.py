"""Time-based train/test split and error metrics (MAE in games)."""
import numpy as np
import pandas as pd

from next82 import config
from next82.features import TARGET


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on older seasons, test on the most recent seasons that have a target."""
    labeled = df[~df.is_forecast]
    first_test = labeled.season_idx.max() - config.N_TEST_SEASONS + 1
    return labeled[labeled.season_idx < first_test], labeled[labeled.season_idx >= first_test]


def is_rotation(df: pd.DataFrame) -> pd.Series:
    """Rotation players' availability matters most to teams and fantasy players."""
    return (df.mpg >= config.ROTATION_MIN_MPG) & (df.gp_share >= config.ROTATION_MIN_GP_SHARE)


def mae_games(df: pd.DataFrame, pred_share: np.ndarray) -> float:
    """Mean absolute error in games, scaled to each target season's length."""
    return float(np.mean(np.abs(pred_share - df[TARGET]) * df.season_games_next))


def score(df: pd.DataFrame, pred_share: np.ndarray) -> dict:
    rot = is_rotation(df).to_numpy()
    comeback = (df.missed_season == 1).to_numpy()
    return {
        "mae_all": mae_games(df, pred_share),
        "mae_rotation": mae_games(df[rot], pred_share[rot]),
        "mae_comeback": mae_games(df[comeback], pred_share[comeback]) if comeback.any() else None,
        "n_all": len(df),
        "n_rotation": int(rot.sum()),
        "n_comeback": int(comeback.sum()),
    }
