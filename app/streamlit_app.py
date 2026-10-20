"""Next82 Streamlit app: search a player, see their forecast and its top factors.

Run:
    streamlit run app/streamlit_app.py
"""
import json
import unicodedata

import altair as alt
import pandas as pd
import streamlit as st

from next82 import config
from next82.explain import GAMES, top_factors
from next82.data import load as load_raw
from next82.train import FORECASTS_PATH, METRICS_PATH

st.set_page_config(page_title="Next82", page_icon="🏀", layout="centered")

# Chart colors (validated for color-vision deficiency and contrast in both themes).
PALETTE = {
    "light": {"up": "#2a78d6", "down": "#e34948", "past": "#2a78d6", "forecast": "#86b6ef", "text": "#52514e"},
    "dark": {"up": "#3987e5", "down": "#e66767", "past": "#3987e5", "forecast": "#184f95", "text": "#c3c2b7"},
}
theme = getattr(st.context, "theme", None)
colors = PALETTE["dark" if theme is not None and theme.type == "dark" else "light"]


def next_season(season: str) -> str:
    start = int(season[:4]) + 1
    return f"{start}-{str(start + 1)[-2:]}"


def normalize(text: str) -> str:
    """Lowercase and strip accents so 'jokic' matches 'Jokić'."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


@st.cache_data
def load():
    if not FORECASTS_PATH.exists():
        return None, None, None
    forecasts = pd.read_parquet(FORECASTS_PATH).sort_values("pred_games", ascending=False)
    forecasts["search"] = forecasts.PLAYER_NAME.map(normalize)
    # Every season each player appeared in, straight from the raw stats. (The model
    # table drops some seasons, e.g. ones whose next-season result isn't known yet.)
    team_games = load_raw("team_games")
    season_games = team_games.groupby(["SEASON", "TEAM_ID"]).size().groupby("SEASON").max().rename("season_games")
    history = load_raw("player_stats")[["PLAYER_ID", "SEASON", "GP"]].merge(season_games, on="SEASON")
    history["season_idx"] = history.SEASON.map(config.SEASONS.index)
    metrics = json.loads(METRICS_PATH.read_text())
    return forecasts, history, metrics


forecasts, history, metrics = load()
if forecasts is None:
    st.error("No forecasts found. Run `python -m next82.data`, `python -m next82.features`, then `python -m next82.train`.")
    st.stop()

current = forecasts.SEASON.iloc[0]
target_season = next_season(current)
mae = metrics["results"][metrics["final_model"]]["mae_all"]

st.title("Next82")
st.caption(f"How many games will a player play in {target_season}? Forecasts are based on seasons through {current}.")

query = st.text_input("Search a player", value=st.query_params.get("player", ""), placeholder="e.g. Embiid, LeBron, Jokic")
matches = forecasts[forecasts.search.str.contains(normalize(query), regex=False)] if query else forecasts.iloc[0:0]

player = None
if query and matches.empty:
    st.warning(f"No player matching “{query}” played in {current}.")
elif len(matches) == 1:
    player = matches.iloc[0]
elif len(matches) > 1:
    matches = matches.sort_values("PLAYER_NAME")
    labels = [f"{r.PLAYER_NAME} ({r.TEAM_ABBREVIATION})" for r in matches.itertuples()]
    choice = st.selectbox(f"{len(matches)} matches", labels, index=None, placeholder="Choose a player")
    if choice is not None:
        player = matches.iloc[labels.index(choice)]


def factor_chart(row: pd.Series) -> alt.Chart:
    top = top_factors(row)
    top["label"] = top.factor + " · " + top.value
    top["direction"] = top.impact_games.map(lambda v: "Adds games" if v >= 0 else "Costs games")
    top["impact_text"] = top.impact_games.map(lambda v: f"{v:+.1f}")
    order = top.label.tolist()
    reach = max(top.impact_games.abs().max(), 1) * 1.25

    # Each row: factor name on top, bar below, so long names don't squeeze the bars on phones.
    y = alt.Y("label:N", sort=order, title=None, axis=None)
    x_scale = alt.Scale(domain=[-reach, reach], nice=False)
    base = alt.Chart(top).encode(y=y)
    bars = base.mark_bar(cornerRadiusEnd=4, height=14, yOffset=9).encode(
        x=alt.X("impact_games:Q", title="Effect on forecast (games)", scale=x_scale),
        color=alt.Color(
            "direction:N",
            scale=alt.Scale(domain=["Adds games", "Costs games"], range=[colors["up"], colors["down"]]),
            legend=alt.Legend(title=None, orient="top"),
        ),
        tooltip=[
            alt.Tooltip("factor:N", title="Factor"),
            alt.Tooltip("value:N", title="Value"),
            alt.Tooltip("impact_text:N", title="Effect (games)"),
        ],
    )
    names = base.mark_text(align="left", baseline="bottom", dy=-2, fontSize=13, color=colors["text"]).encode(
        x=alt.datum(-reach, scale=x_scale), text="label:N"
    )
    text = dict(x=alt.X("impact_games:Q"), text="impact_text:N")
    up_labels = base.transform_filter("datum.impact_games >= 0").mark_text(
        align="left", dx=6, yOffset=9, color=colors["text"]
    ).encode(**text)
    down_labels = base.transform_filter("datum.impact_games < 0").mark_text(
        align="right", dx=-6, yOffset=9, color=colors["text"]
    ).encode(**text)
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(opacity=0.4).encode(x=alt.X("x:Q", scale=x_scale))
    return (bars + names + up_labels + down_labels + zero).properties(height=alt.Step(52))


def history_chart(row: pd.Series) -> alt.Chart:
    h = history[history.PLAYER_ID == row.PLAYER_ID].set_index("season_idx")
    # Seasons after a player's first appearance with no record were missed entirely.
    h = h.reindex(range(h.index.min(), len(config.SEASONS)))
    h["SEASON"] = [config.SEASONS[i] for i in h.index]
    h["GP"] = h.GP.fillna(0)
    h["season_games"] = h.season_games.fillna(GAMES)
    h["kind"] = "Played"
    h["note"] = h.GP.astype(int).astype(str) + " of " + h.season_games.astype(int).astype(str)
    h.loc[h.GP == 0, "note"] = "Missed season"

    fc = pd.DataFrame({
        "SEASON": [f"{target_season}"],
        "GP": [round(row.pred_games)],
        "kind": ["Forecast"],
        "note": [f"Forecast: {row.pred_games:.0f} of {GAMES} (typical error ±{mae:.0f})"],
    })
    data = pd.concat([h[["SEASON", "GP", "kind", "note"]], fc], ignore_index=True)

    x = alt.X("SEASON:N", title=None, sort=None, axis=alt.Axis(labelAngle=0))
    missed = alt.Chart(data[data.note == "Missed season"]).mark_text(
        text="Missed", baseline="bottom", dy=-4, fontSize=11, color=colors["text"]
    ).encode(x=x, y=alt.Y("GP:Q"))
    bars = alt.Chart(data).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=x,
        y=alt.Y("GP:Q", title="Games played", scale=alt.Scale(domain=[0, GAMES])),
        color=alt.Color(
            "kind:N",
            scale=alt.Scale(domain=["Played", "Forecast"], range=[colors["past"], colors["forecast"]]),
            legend=alt.Legend(title=None, orient="top"),
        ),
        tooltip=[alt.Tooltip("SEASON:N", title="Season"), alt.Tooltip("note:N", title="Games")],
    )
    return (bars + missed).properties(height=260)


if player is not None:
    st.subheader(f"{player.PLAYER_NAME} · {player.TEAM_ABBREVIATION}")

    comeback = bool(player.missed_season)
    c1, c2, c3 = st.columns(3)
    change = None if comeback else f"{player.pred_games - player.gp_share * GAMES:+.0f} vs. {current}"
    c1.metric(f"{target_season} forecast", f"{player.pred_games:.0f} games", change)
    c2.metric(f"Played in {current}", "Missed season" if comeback else f"{player.GP} of {player.season_games}")
    c3.metric("Age", f"{player.age:.0f}")
    if comeback:
        st.info(
            f"{player.PLAYER_NAME} didn't play in {current}. This is a comeback forecast, based on what happened "
            "to past players returning from a missed season. Their results varied widely: some played nearly "
            "every game, others missed a second season.",
            icon="ℹ️",
        )
    st.caption(f"Out of {GAMES} games. Forecasts are off by about {mae:.0f} games on average, so treat this as a range, not an exact count.")

    st.markdown("#### What's driving the forecast")
    st.caption(
        f"The average player is forecast at {player.shap_base:.0f} games. "
        "Each bar shows how much one factor moves this player's forecast up or down."
    )
    st.altair_chart(factor_chart(player), width="stretch")

    st.markdown("#### Games played by season")
    st.altair_chart(history_chart(player), width="stretch")

elif not query:
    st.markdown(f"#### All {target_season} forecasts")
    table = forecasts.assign(
        played=forecasts.GP.astype(str) + " of " + forecasts.season_games.astype(str),
        forecast=forecasts.pred_games.round().astype(int),
    )[["PLAYER_NAME", "TEAM_ABBREVIATION", "age", "played", "forecast"]]
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "PLAYER_NAME": "Player",
            "TEAM_ABBREVIATION": "Team",
            "age": st.column_config.NumberColumn("Age", format="%d"),
            "played": f"Played in {current}",
            "forecast": st.column_config.ProgressColumn(
                f"{target_season} forecast", min_value=0, max_value=GAMES, format="%d games"
            ),
        },
    )

with st.expander("How it works"):
    results = pd.DataFrame(metrics["results"]).T
    results = results.rename(
        columns={"mae_all": "All players", "mae_rotation": "Rotation players", "mae_comeback": "Comeback seasons"}
    )
    st.markdown(
        f"""
A LightGBM model trained on NBA seasons from 2015-16 to {current}. It uses age, minutes,
games missed, long absences and the last few seasons of history. Injury data isn't
available, so long absences come from comparing each player's game log with their team's schedule.

**Accuracy.** Each model was trained on {metrics['train_seasons'][0]} to {metrics['train_seasons'][1]}
and tested on {metrics['test_seasons'][0]} to {metrics['test_seasons'][1]}, which it never saw.
Average error in games:
"""
    )
    cols = ["All players", "Rotation players", "Comeback seasons"]
    st.dataframe(results[cols].astype(float).round(1), width="stretch")
    n_comeback = next(iter(metrics["results"].values()))["n_comeback"]
    st.caption(
        "Rotation players: 15+ minutes per game and at least a quarter of their team's games. "
        f"Comeback seasons: the season after a player missed a whole season (only {n_comeback} in the test "
        "seasons, so that column is less reliable)."
    )
