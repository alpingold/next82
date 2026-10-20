"""Evaluate all models, then train the final model and write next-season forecasts.

Outputs:
    models/metrics.json               test-set error for each model
    models/lightgbm.joblib            final model trained on all labeled seasons
    data/processed/forecasts.parquet  one row per player: forecast + SHAP values

Usage:
    python -m next82.train
"""
import json

import joblib
import pandas as pd

from next82 import config, evaluate, explain, models
from next82.features import FEATURES, load_table

FINAL_MODEL = "LightGBM"
MODEL_PATH = config.MODELS_DIR / "lightgbm.joblib"
METRICS_PATH = config.MODELS_DIR / "metrics.json"
FORECASTS_PATH = config.PROCESSED_DIR / "forecasts.parquet"


def run_evaluation(df: pd.DataFrame) -> dict:
    train, test = evaluate.split(df)
    results = {name: evaluate.score(test, models.predict(models.fit(name, train), test)) for name in models.MODELS}

    print(f"Train: {train.SEASON.min()} to {train.SEASON.max()} ({len(train):,} rows)")
    print(f"Test:  {test.SEASON.min()} to {test.SEASON.max()} ({len(test):,} rows)\n")
    print(f"{'Model':20s} {'MAE all':>8s} {'MAE rotation':>13s}")
    for name, r in results.items():
        print(f"{name:20s} {r['mae_all']:8.2f} {r['mae_rotation']:13.2f}")

    return {
        "train_seasons": [train.SEASON.min(), train.SEASON.max()],
        "test_seasons": [test.SEASON.min(), test.SEASON.max()],
        "final_model": FINAL_MODEL,
        "results": results,
    }


def train_final(df: pd.DataFrame):
    labeled, upcoming = df[~df.is_forecast], df[df.is_forecast].copy()
    model = models.fit(FINAL_MODEL, labeled)

    upcoming["pred_share"] = models.predict(model, upcoming)
    upcoming["pred_games"] = upcoming.pred_share * explain.GAMES
    values, base = explain.shap_values(model, upcoming)
    for i, f in enumerate(FEATURES):
        upcoming[f"shap_{f}"] = values[:, i]
    upcoming["shap_base"] = base
    return model, upcoming


def main():
    df = load_table()
    metrics = run_evaluation(df)
    model, forecasts = train_final(df)

    config.MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    forecasts.to_parquet(FORECASTS_PATH, index=False)
    print(f"\nSaved {len(forecasts)} forecasts for the season after {forecasts.SEASON.iloc[0]}")


if __name__ == "__main__":
    main()
