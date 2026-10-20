# Next82

Forecasts how many games an NBA player will play next season and explains what drives each prediction.

## Setup

```bash
brew install libomp            # macOS only, required by LightGBM
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Pipeline

```bash
python -m next82.data        # download raw data from nba_api (~2 min, skips files already present)
python -m next82.features    # build data/processed/player_seasons.parquet
python -m next82.train       # evaluate models, train final model, write forecasts
streamlit run app/streamlit_app.py
```

Link straight to a player with `?player=<name>`, e.g. `http://localhost:8501/?player=Embiid`.

## How it works

- **Data:** regular-season stats, bios and game logs for 2015-16 to 2025-26.
- **Target:** next season's games played as a share of the schedule, so the shortened
  2019-20 and 2020-21 seasons compare fairly. A player who misses the whole next season
  and returns later counts as 0. Players who never return are dropped.
- **Features (23):** age, experience, size, games and minutes played, usage, and absences
  estimated by matching game logs to team schedules (longest absence, 10+ game absences,
  games missed at the start/end of the season), plus the last 1-3 seasons of history.
- **Models:** "same as last year" and 3-year-average baselines, ridge regression, LightGBM.
- **Evaluation:** train on 2015-16 to 2022-23, test on 2023-24 and 2024-25.
- **Explanations:** SHAP values from LightGBM, shown in games.

## Results (test seasons, average error in games)

| Model | All players | Rotation players |
|---|---|---|
| Same as last year | 17.6 | 16.7 |
| 3-year average | 17.2 | 16.2 |
| Linear regression | 15.6 | 14.9 |
| **LightGBM** | **15.6** | **14.7** |

Rotation players: 15+ minutes per game and at least a quarter of their team's games.

## Layout

```
data/raw/          raw pulls from nba_api (gitignored)
data/processed/    player_seasons.parquet, forecasts.parquet (gitignored)
models/            lightgbm.joblib, metrics.json (gitignored)
notebooks/         exploration
src/next82/
  config.py        paths, seasons, settings
  data.py          nba_api collection
  features.py      modeling table
  models.py        baselines, linear regression, LightGBM
  evaluate.py      time-based split, MAE in games
  explain.py       SHAP factors with readable labels
  train.py         evaluation + final model + forecasts
app/               Streamlit app
.streamlit/        app theme
tests/
```

## Limitations

- nba_api has no injury data. Absences are inferred from game logs, so rest days,
  suspensions and falling out of the rotation look the same as injuries.
- Forecasts assume the player is in the league next season.
