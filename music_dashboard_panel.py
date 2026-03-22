import pandas as pd
import ast
import panel as pn
import hvplot.pandas

pn.extension('tabulator')

# ---- data loading / cleaning (same as notebook) ----
df = pd.read_csv("track_data_final.csv")

df["album_release_date"] = pd.to_datetime(df["album_release_date"], errors="coerce")
df["year"] = df["album_release_date"].dt.year
df["duration_min"] = (df["track_duration_ms"] / 60000.0).round(2)

def parse_genres(x):
    if pd.isna(x) or x == "" or x == "[]":
        return []
    try:
        return ast.literal_eval(x)
    except (ValueError, SyntaxError):
        return []

df["genre_list"] = df["artist_genres"].apply(parse_genres)

def main_genre(genres):
    if genres:
        return genres[0]
    return "Unknown"

df["main_genre"] = df["genre_list"].apply(main_genre)

dash_cols = [
    "track_name", "artist_name", "album_name", "album_type",
    "track_popularity", "artist_popularity",
    "duration_min", "explicit", "year", "main_genre"
]

dash_df = df[dash_cols].dropna(subset=["track_popularity", "artist_popularity", "year"])
dash_df["track_popularity"] = dash_df["track_popularity"].astype(int)
dash_df["artist_popularity"] = dash_df["artist_popularity"].astype(int)
dash_df["year"] = dash_df["year"].astype(int)

# ---- widgets, filter function, plots, top_table, dashboard ----
# (paste exactly the Panel code you now have working in the notebook:
#  genre_widget, year_slider, filter_df, filtered, scatter, bar,
#  duration_box, trend, top_table, top_table_pane, controls, plots, dashboard)


# Widgets
genre_widget = pn.widgets.MultiSelect(
    name="Genre",
    options=sorted(dash_df["main_genre"].unique()),
    value=["pop"],
    size=8
)

year_slider = pn.widgets.IntRangeSlider(
    name="Year range",
    start=int(dash_df["year"].min()),
    end=int(dash_df["year"].max()),
    value=(int(dash_df["year"].min()), int(dash_df["year"].max()))
)

# Plain Python function to filter the DataFrame
def filter_df(genres, year_range):
    dff = dash_df.copy()
    if genres:
        dff = dff[dff["main_genre"].isin(genres)]
    if year_range and len(year_range) == 2:
        dff = dff[(dff["year"] >= year_range[0]) & (dff["year"] <= year_range[1])]
    return dff

# Bound, reactive DataFrame
filtered = pn.bind(filter_df, genres=genre_widget, year_range=year_slider)

# 1) Scatter: track vs artist popularity
scatter = pn.bind(
    lambda df: df.hvplot.scatter(
        x="artist_popularity",
        y="track_popularity",
        by="main_genre",
        hover_cols=["track_name", "artist_name", "album_name", "album_type", "year"],
        title="Track vs Artist Popularity",
        height=350, width=450,
    ),
    df=filtered
)

# 2) Bar: average popularity by genre
def make_bar(df):
    genre_mean = (
        df.groupby("main_genre")["track_popularity"]
        .mean()
        .sort_values(ascending=False)
        .head(12)
    )
    if genre_mean.empty:
        return genre_mean.hvplot.bar().opts(title="No data for selected filters")
    return genre_mean.hvplot.bar(
        rot=45,
        ylabel="Avg track popularity",
        xlabel="Genre",
        title="Average Track Popularity by Genre",
        height=350, width=450,
    )

bar = pn.bind(make_bar, df=filtered)

# 3) Duration vs album type (box plot)
duration_box = pn.bind(
    lambda df: df.hvplot.box(
        y="duration_min",
        by="album_type",
        ylabel="Duration (min)",
        xlabel="Album type",
        title="Track Duration by Album Type",
        height=350, width=450,
    ),
    df=filtered
)

# 4) Popularity trend over time
def make_trend(df):
    year_mean = df.groupby("year")["track_popularity"].mean()
    if year_mean.empty:
        return year_mean.hvplot.line().opts(title="No data for selected filters")
    return year_mean.hvplot.line(
        ylabel="Avg track popularity",
        xlabel="Year",
        title="Popularity Over Time",
        height=350, width=450,
    )


trend = pn.bind(make_trend, df=filtered)

# 5) Top tracks table (NEW)
top_table = pn.bind(
    lambda df: df.sort_values("track_popularity", ascending=False)
                 .head(10)
                 [["track_name", "artist_name", "track_popularity", "year", "main_genre"]],
    df=filtered
)

top_table_pane = pn.widgets.Tabulator(top_table, height=250)


# Layout with Panel
controls = pn.Column("## Filters", genre_widget, year_slider)

plots = pn.Column(
    pn.Row(scatter, bar),
    pn.Row(duration_box, trend),
    pn.Row(top_table_pane),
)

dashboard = pn.Row(controls, plots)

if __name__ == "__main__":
    pn.serve(dashboard, show=True)

