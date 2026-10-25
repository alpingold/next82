"""Export the forecasts as JSON for the website (web/).

Reads the small committed app files, so it runs without the full dataset:
    web/public/data/index.json         meta, teams, and a summary row per player
    web/public/data/players/<id>.json  one player's factors, history and similar comebacks

Usage:
    python -m next82.export
"""
import json
import math
import shutil
import unicodedata
from datetime import datetime

import pandas as pd

from next82 import config, data
from next82.explain import GAMES, similar_comebacks, top_factors
from next82.train import FORECASTS_PATH, HISTORY_PATH, METRICS_PATH, PAST_COMEBACKS_PATH

OUT_DIR = config.ROOT / "web" / "public" / "data"


def next_season(season: str) -> str:
    start = int(season[:4]) + 1
    return f"{start}-{str(start + 1)[-2:]}"


def plain(text: str) -> str:
    """Accent-free lowercase text for search: 'Nikola Jokić' -> 'nikola jokic'."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def clean(value):
    """JSON-safe values: NaN -> None, numpy numbers -> Python numbers."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, separators=(",", ":"), allow_nan=False))


def player_history(history: pd.DataFrame, seasons: list[str], player_id: int) -> list[dict]:
    """Games per season from the player's first season on; seasons with no record were missed."""
    h = history[history.PLAYER_ID == player_id].set_index("SEASON")
    h = h.reindex(seasons[seasons.index(h.index.min()):])
    season_length = history.groupby("SEASON").season_games.max()
    return [
        {"season": s, "games": int(r.GP) if pd.notna(r.GP) else 0,
         "seasonGames": int(season_length[s]), "missed": pd.isna(r.GP)}
        for s, r in h.iterrows()
    ]


def round_or_none(value, digits=1):
    return None if pd.isna(value) else round(float(value), digits)


def main():
    forecasts = pd.read_parquet(FORECASTS_PATH)
    history = pd.read_parquet(HISTORY_PATH)
    past = pd.read_parquet(PAST_COMEBACKS_PATH)
    metrics = json.loads(METRICS_PATH.read_text())

    current = forecasts.SEASON.iloc[0]
    target = next_season(current)
    seasons = sorted(history.SEASON.unique())
    rosters = data.saved_rosters(target)

    if rosters is not None:
        now = rosters.set_index("PLAYER_ID")[["TEAM_ABBREVIATION", "TEAM_FULL_NAME"]]
        forecasts = forecasts.join(now, on="PLAYER_ID", rsuffix="_NOW")
    else:
        forecasts["TEAM_ABBREVIATION_NOW"] = None
        forecasts["TEAM_FULL_NAME"] = None

    comeback = forecasts.missed_season == 1
    forecasts["shown"] = forecasts.games_if_healthy.where(comeback, forecasts.pred_games)
    # Search suggestions list the best-known players first: minutes in their last season played.
    recent_mpg = forecasts.mpg.fillna(forecasts.mpg_lag1)
    forecasts["recent_minutes"] = (recent_mpg * forecasts.last_played_gp_share * GAMES).fillna(0)
    forecasts = forecasts.sort_values("shown", ascending=False)

    players = []
    if (OUT_DIR / "players").exists():
        shutil.rmtree(OUT_DIR / "players")
    for _, r in forecasts.iterrows():
        is_comeback = bool(r.missed_season)
        summary = {
            "id": int(r.PLAYER_ID),
            "name": r.PLAYER_NAME,
            "search": plain(r.PLAYER_NAME),
            "team": r.TEAM_ABBREVIATION_NOW if pd.notna(r.TEAM_ABBREVIATION_NOW) else None,
            "lastTeam": r.TEAM_ABBREVIATION,
            "age": int(r.age),
            "games": int(r.GP),
            "seasonGames": int(r.season_games),
            "comeback": is_comeback,
            "forecast": round_or_none(r.pred_games),
            "ifHealthy": round_or_none(r.games_if_healthy) if is_comeback else None,
            "setbackChance": round_or_none(r.p_setback, 3) if is_comeback else None,
            "shown": round_or_none(r.shown),
            "recentMinutes": round(float(r.recent_minutes)),
        }
        players.append(summary)

        factors = top_factors(r)
        detail = summary | {
            "teamName": r.TEAM_FULL_NAME if pd.notna(r.TEAM_FULL_NAME) else None,
            "factorBase": round(float(r.shap_base), 1),
            "factors": [
                {"label": f.factor, "value": f.value, "games": round(float(f.impact_games), 2)}
                for f in factors.itertuples()
            ],
            "history": player_history(history, seasons, r.PLAYER_ID),
            "similar": [
                {"name": s.player, "seasonMissed": s.missed, "age": int(s.age), "before": s.before,
                 "comebackGames": int(s.comeback_games)}
                for s in similar_comebacks(r, past).itertuples()
            ] if is_comeback else [],
        }
        write_json(OUT_DIR / "players" / f"{int(r.PLAYER_ID)}.json", detail)

    teams = []
    if rosters is not None:
        forecast_ids = set(forecasts.PLAYER_ID)
        for (abbr, name), roster in rosters.groupby(["TEAM_ABBREVIATION", "TEAM_FULL_NAME"]):
            teams.append({
                "abbr": abbr,
                "name": name,
                "noForecast": sorted(roster.loc[~roster.PLAYER_ID.isin(forecast_ids), "PLAYER_NAME"]),
            })
        teams.sort(key=lambda t: t["name"])

    results = metrics["results"]
    model_mae = results[metrics["final_model"]]["mae_all"]
    best_baseline = min(("Same as last year", "3-year average"), key=lambda k: results[k]["mae_all"])
    write_json(OUT_DIR / "index.json", {
        "meta": {
            "forecastSeason": target,
            "dataThrough": current,
            "previousSeason": seasons[-2],
            "latestFinishedSeason": config.SEASONS[-1],
            "rostersAsOf": rosters.FETCHED_AT.iloc[0].isoformat() if rosters is not None else None,
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "games": GAMES,
            "setbackGames": config.SETBACK_GAMES,
            "accuracy": {
                "modelMae": round(model_mae, 1),
                "bestBaseline": best_baseline,
                "bestBaselineMae": round(results[best_baseline]["mae_all"], 1),
                "comebackHealthyMae": round(metrics["comeback"]["mae_healthy_two_part"], 1),
                "testSeasons": metrics["test_seasons"],
            },
        },
        "teams": teams,
        "players": players,
    })
    size = sum(p.stat().st_size for p in OUT_DIR.rglob("*.json"))
    where = OUT_DIR.relative_to(config.ROOT) if OUT_DIR.is_relative_to(config.ROOT) else OUT_DIR
    print(f"Exported {len(players)} players and {len(teams)} teams to {where} ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
