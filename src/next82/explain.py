"""Per-prediction explanations (top factors behind each forecast).

Uses SHAP values from the LightGBM model. Each feature's SHAP value is how much
it moved the forecast away from the average forecast, converted here to games
out of 82.
"""
import numpy as np
import pandas as pd
import shap

from next82.features import FEATURES

GAMES = 82

LABELS = {
    "age": "Age",
    "years_since_draft": "Years since draft",
    "undrafted": "Undrafted",
    "height_in": "Height",
    "weight_lb": "Weight",
    "gp_share": "Games played this season",
    "mpg": "Minutes per game",
    "min_share": "Total minutes this season vs. league leader",
    "usg_pct": "Usage rate",
    "longest_gap": "Longest absence this season",
    "n_major_gaps": "Absences of 10+ games this season",
    "missed_start": "Games missed at start of season",
    "missed_end": "Games missed at end of season",
    "n_teams": "Teams played for this season",
    "missed_season": "Missed all of this season",
    "gp_share_lag1": "Games played last season",
    "gp_share_lag2": "Games played two seasons ago",
    "missed_season_lag1": "Missed all of last season",
    "mpg_lag1": "Minutes per game last season",
    "longest_gap_lag1": "Longest absence last season",
    "missed_end_lag1": "Games missed at end of last season",
    "major_gaps_3yr": "Absences of 10+ games, last 3 seasons",
    "avg_gp_share_3yr": "Average games played, last 3 seasons",
    "seasons_in_data": "Seasons in the NBA since 2015-16",
}


def format_value(feature: str, value) -> str:
    """Human-readable value for a feature, e.g. '38 of 82 games'."""
    if pd.isna(value):
        return "no data"
    if feature in ("gp_share", "gp_share_lag1", "gp_share_lag2", "avg_gp_share_3yr"):
        return f"{value * GAMES:.0f} of {GAMES} games"
    if feature in ("longest_gap", "missed_start", "missed_end", "longest_gap_lag1", "missed_end_lag1"):
        return f"{value:.0f} games"
    if feature in ("undrafted", "missed_season", "missed_season_lag1"):
        return "yes" if value else "no"
    if feature in ("mpg", "mpg_lag1"):
        return f"{value:.1f}"
    if feature in ("usg_pct", "min_share"):
        return f"{value:.0%}"
    if feature == "height_in":
        return f"{int(value) // 12}'{int(value) % 12}\""
    if feature == "weight_lb":
        return f"{value:.0f} lb"
    return f"{value:.0f}"


def shap_values(model, X: pd.DataFrame) -> tuple[np.ndarray, float]:
    """SHAP values in games (rows x features) and the base value in games."""
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X[FEATURES]) * GAMES
    return values, float(np.ravel(explainer.expected_value)[0]) * GAMES


def top_factors(row: pd.Series, n: int = 6) -> pd.DataFrame:
    """Largest factors for one player, from a forecast row holding shap_<feature> columns."""
    impact = pd.Series({f: row[f"shap_{f}"] for f in FEATURES})
    top = impact.reindex(impact.abs().sort_values(ascending=False).index[:n])
    return pd.DataFrame({
        "factor": [LABELS[f] for f in top.index],
        "value": [
            "did not play" if row.get("missed_season") and pd.isna(row[f]) else format_value(f, row[f])
            for f in top.index
        ],
        "impact_games": top.to_numpy(),
    })
