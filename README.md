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
- **Missed seasons:** a season a player sits out entirely gets its own row (0 games), so the
  model learns what happens in comeback years. Rotation players who sat out the latest season
  (e.g. Tyrese Haliburton, Damian Lillard) get a comeback forecast.
- **Features (24):** age, experience, size, games and minutes played, usage, and absences
  estimated by matching game logs to team schedules (longest absence, 10+ game absences,
  games missed at the start/end of the season), plus the last 1-3 seasons of history.
- **Models:** "same as last year" and 3-year-average baselines, ridge regression, LightGBM.
- **Evaluation:** train on 2015-16 to 2022-23, test on 2023-24 and 2024-25.
- **Explanations:** SHAP values from LightGBM, shown in games.

## Results (test seasons, average error in games)

| Model | All players | Rotation players | Comeback seasons* |
|---|---|---|---|
| Same as last year | 17.8 | 16.8 | 15.6 |
| 3-year average | 17.2 | 16.3 | 14.1 |
| Linear regression | 15.7 | 15.0 | 14.2 |
| **LightGBM** | **15.7** | **14.8** | **13.5** |

Rotation players: 15+ minutes per game and at least a quarter of their team's games.
*Comeback seasons: the season after a player sat out a whole season. There are only 31 in the
test seasons, so this column uses all 161 comebacks from 2018-19 on, each predicted by a model
trained only on earlier seasons.

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
