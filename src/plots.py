"""
Plotting helpers for the City Bike-Share project.

Every function takes a tidy pandas DataFrame (the result of a SQL query),
draws one chart with a consistent style, optionally saves it as a PNG and
returns the matplotlib Figure. Keeping the plotting code here keeps the
notebook focused on the analysis itself.
"""
from __future__ import annotations

import os
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Style
# --------------------------------------------------------------------------
COLORS = {
    "member": "#2E6F9E",
    "casual": "#F28E2B",
    "classic_bike": "#4C78A8",
    "electric_bike": "#59A14F",
    "docked_bike": "#B07AA1",
    "highlight": "#D1495B",
    "neutral": "#9AA5B1",
    "positive": "#2A9D8F",
    "negative": "#D1495B",
}
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BIKE_LABELS = {"classic_bike": "Classic", "electric_bike": "Electric", "docked_bike": "Docked"}

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 160,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "font.size": 10,
})


def _finish(fig, title: str, subtitle: Optional[str], save_path: Optional[str]):
    """Add title/subtitle to the main axes, tighten layout and optionally save."""
    ax = fig.axes[0]
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold",
                 pad=26 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=9.5, color="#555555")
    fig.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", facecolor="white")
    return fig


def _millions(x, _pos=None):
    if x == 0:
        return "0"
    if abs(x) >= 1e6:
        return f"{x / 1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"{x / 1e3:.1f}".rstrip("0").rstrip(".") + "K"
    return f"{x:.0f}"


def _short(name: str, n: int = 34) -> str:
    name = str(name)
    return name if len(name) <= n else name[: n - 1] + "…"


# --------------------------------------------------------------------------
# 1. Fleet / rider mix
# --------------------------------------------------------------------------
def plot_fleet_mix(df: pd.DataFrame, save_path: Optional[str] = None):
    """Grouped bars: rides by bike type, split by rider type.
    df columns: rideable_type, member_casual, number_of_rides"""
    pivot = df.pivot_table(index="rideable_type", columns="member_casual",
                           values="number_of_rides", aggfunc="sum")
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    total = pivot.values.sum()

    fig, ax = plt.subplots(figsize=(8.5, 5))
    x = np.arange(len(pivot))
    w = 0.38
    for i, rider in enumerate(["member", "casual"]):
        bars = ax.bar(x + (i - 0.5) * w, pivot[rider], w, label=rider.title(),
                      color=COLORS[rider])
        for b in bars:
            ax.annotate(f"{b.get_height() / 1e6:.2f}M\n({b.get_height() / total:.0%})",
                        (b.get_x() + b.get_width() / 2, b.get_height()),
                        ha="center", va="bottom", fontsize=8.5, xytext=(0, 3),
                        textcoords="offset points")
    ax.set_xticks(x)
    ax.set_xticklabels([BIKE_LABELS.get(i, i) for i in pivot.index])
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.set_ylabel("Number of rides")
    ax.set_ylim(0, pivot.values.max() * 1.22)
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    return _finish(fig, "Rides by bike type and rider type",
                   "Share of all rides shown in brackets", save_path)


# --------------------------------------------------------------------------
# 2. Demand over time
# --------------------------------------------------------------------------
def plot_hourly_overall(df: pd.DataFrame, save_path: Optional[str] = None):
    """Bars: trips per start hour, top-3 hours highlighted.
    df columns: hour_of_day, number_of_trips"""
    d = df.copy()
    d["hour_of_day"] = d["hour_of_day"].astype(int)
    d = d.groupby("hour_of_day", as_index=False)["number_of_trips"].sum().sort_values("hour_of_day")
    top3 = set(d.nlargest(3, "number_of_trips")["hour_of_day"])
    colors = [COLORS["highlight"] if h in top3 else COLORS["neutral"] for h in d["hour_of_day"]]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(d["hour_of_day"], d["number_of_trips"], color=colors)
    ax.set_xticks(range(24))
    ax.set_xlabel("Hour of day (trip start)")
    ax.set_ylabel("Number of trips")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.grid(axis="x", visible=False)
    peak = d.loc[d["number_of_trips"].idxmax()]
    return _finish(fig, "When does demand peak? Trips by hour of day",
                   f"Busiest hour: {int(peak['hour_of_day']):02d}:00 "
                   f"({peak['number_of_trips'] / 1e6:.2f}M trips). Top-3 hours highlighted.",
                   save_path)


def plot_hourly_by_rider(df: pd.DataFrame, save_path: Optional[str] = None):
    """Lines: share of each rider type's trips by hour (shows commute vs leisure).
    df columns: hour_of_day, member_casual, number_of_trips"""
    d = df.copy()
    d["hour_of_day"] = d["hour_of_day"].astype(int)
    d["share"] = d["number_of_trips"] / d.groupby("member_casual")["number_of_trips"].transform("sum")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for rider in ["member", "casual"]:
        s = d[d["member_casual"] == rider].sort_values("hour_of_day")
        ax.plot(s["hour_of_day"], s["share"], marker="o", ms=4, lw=2,
                color=COLORS[rider], label=rider.title())
    ax.set_xticks(range(24))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Hour of day (trip start)")
    ax.set_ylabel("Share of rider type's trips")
    ax.legend(frameon=False)
    return _finish(fig, "Hourly demand profile: members vs casual riders",
                   "Each line sums to 100% so the two groups can be compared on shape", save_path)


def plot_weekday(df: pd.DataFrame, save_path: Optional[str] = None):
    """Bars: trips per weekday with busiest/quietest highlighted.
    df columns: Day (full weekday name), Number_of_Trips"""
    d = df.set_index("Day").reindex(DAY_ORDER)["Number_of_Trips"]
    colors = [COLORS["highlight"] if v == d.max() else COLORS["positive"] if v == d.min()
              else COLORS["neutral"] for v in d]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.bar(d.index, d.values, color=colors)
    for b in bars:
        ax.annotate(f"{b.get_height() / 1e6:.2f}M", (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom", fontsize=9, xytext=(0, 3), textcoords="offset points")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.set_ylim(0, d.max() * 1.12)
    ax.set_ylabel("Number of trips")
    ax.grid(axis="x", visible=False)
    gap = 1 - d.min() / d.max()
    return _finish(fig, "Trips by day of week",
                   f"{d.idxmax()} is busiest, {d.idxmin()} is quietest "
                   f"({gap:.0%} fewer trips than the busiest day)", save_path)


def plot_heatmap(df: pd.DataFrame, save_path: Optional[str] = None):
    """Heatmap weekday x hour. df columns: Day, hour_of_day, number_of_trips"""
    p = df.pivot_table(index="Day", columns="hour_of_day", values="number_of_trips",
                       aggfunc="sum").reindex(DAY_ORDER)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    im = ax.imshow(p.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(p.shape[1]))
    ax.set_xticklabels([int(c) for c in p.columns])
    ax.set_yticks(range(len(p.index)))
    ax.set_yticklabels(p.index)
    ax.grid(False)
    ax.set_xlabel("Hour of day")
    cb = fig.colorbar(im, ax=ax, pad=0.01)
    cb.formatter = mtick.FuncFormatter(_millions)
    cb.update_ticks()
    return _finish(fig, "Demand heatmap: weekday x hour",
                   "Darker = more trips. Compare the weekday and weekend shapes.", save_path)


def plot_monthly_trend(df: pd.DataFrame, save_path: Optional[str] = None):
    """Lines: monthly trips, one line per year. df columns: year, month, trips.
    Partial years (first/last) simply have fewer points."""
    fig, ax = plt.subplots(figsize=(10, 5))
    years = sorted(df["year"].unique())
    cmap = plt.get_cmap("viridis")
    for i, y in enumerate(years):
        s = df[df["year"] == y].sort_values("month")
        ax.plot(s["month"], s["trips"], marker="o", ms=4, lw=2,
                color=cmap(i / max(len(years) - 1, 1)), label=str(y))
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.set_ylabel("Trips per month")
    ax.legend(title="Year", frameon=False, ncol=len(years))
    return _finish(fig, "Seasonality: monthly trips by year",
                   "2020 starts in May and 2024 ends in August (partial years)", save_path)


def plot_daily_trend(df: pd.DataFrame, save_path: Optional[str] = None):
    """Daily trips with 30-day rolling mean. df columns: trip_date, trips"""
    d = df.copy()
    d["trip_date"] = pd.to_datetime(d["trip_date"])
    d = d.sort_values("trip_date")
    d["rolling"] = d["trips"].rolling(30, center=True, min_periods=10).mean()
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(d["trip_date"], d["trips"], color=COLORS["neutral"], alpha=0.45, lw=0.8, label="Daily trips")
    ax.plot(d["trip_date"], d["rolling"], color=COLORS["member"], lw=2.4, label="30-day average")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.set_ylabel("Trips per day")
    ax.legend(frameon=False)
    return _finish(fig, "Daily ridership over time",
                   "Grey = every day, blue = 30-day rolling average", save_path)


def plot_bike_share_trend(df: pd.DataFrame, save_path: Optional[str] = None):
    """Stacked area: share of monthly trips by bike type.
    df columns: year, month, rideable_type, trips"""
    d = df.copy()
    d["period"] = pd.to_datetime(dict(year=d["year"], month=d["month"], day=1))
    p = d.pivot_table(index="period", columns="rideable_type", values="trips", aggfunc="sum").fillna(0)
    p = p.div(p.sum(axis=1), axis=0)
    cols = [c for c in ["classic_bike", "electric_bike", "docked_bike"] if c in p.columns]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.stackplot(p.index, [p[c] for c in cols], labels=[BIKE_LABELS[c] for c in cols],
                 colors=[COLORS[c] for c in cols], alpha=0.9)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, 1)
    ax.set_ylabel("Share of monthly trips")
    ax.legend(loc="upper left", frameon=False, ncol=3)
    return _finish(fig, "Bike-type mix over time",
                   "How the share of classic, electric and docked bikes has shifted", save_path)


# --------------------------------------------------------------------------
# 3. Rider behaviour
# --------------------------------------------------------------------------
def plot_duration_distribution(df: pd.DataFrame, save_path: Optional[str] = None):
    """Share of each rider type's trips by trip length (minutes, 1-59).
    df columns: member_casual, minute, trips"""
    d = df.copy()
    d["share"] = d["trips"] / d.groupby("member_casual")["trips"].transform("sum")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for rider in ["member", "casual"]:
        s = d[d["member_casual"] == rider].sort_values("minute")
        ax.plot(s["minute"], s["share"], lw=2.4, color=COLORS[rider], label=rider.title())
        ax.fill_between(s["minute"], s["share"], alpha=0.12, color=COLORS[rider])
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Trip duration (minutes)")
    ax.set_ylabel("Share of rider type's trips")
    ax.legend(frameon=False)
    return _finish(fig, "Trip duration: members vs casual riders",
                   "Cleaned trips shorter than 60 minutes, as a share of each rider type's trips",
                   save_path)


def plot_avg_duration(df: pd.DataFrame, save_path: Optional[str] = None):
    """Grouped bars: average trip length by bike type and rider type.
    df columns: rideable_type, member_casual, avg_duration_min"""
    p = df.pivot_table(index="rideable_type", columns="member_casual", values="avg_duration_min")
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    x = np.arange(len(p))
    w = 0.38
    for i, rider in enumerate(["member", "casual"]):
        bars = ax.bar(x + (i - 0.5) * w, p[rider], w, color=COLORS[rider], label=rider.title())
        for b in bars:
            ax.annotate(f"{b.get_height():.1f}", (b.get_x() + b.get_width() / 2, b.get_height()),
                        ha="center", va="bottom", fontsize=9, xytext=(0, 3), textcoords="offset points")
    ax.set_xticks(x)
    ax.set_xticklabels([BIKE_LABELS.get(i, i) for i in p.index])
    ax.set_ylabel("Average trip duration (minutes)")
    ax.set_ylim(0, p.values.max() * 1.15)
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    return _finish(fig, "Average trip duration by bike type and rider type",
                   "Cleaned data: trips between 1 minute and 24 hours", save_path)


# --------------------------------------------------------------------------
# 4. Stations
# --------------------------------------------------------------------------
def plot_station_bars(df: pd.DataFrame, value_col: str, title: str, subtitle: Optional[str] = None,
                      color: str = COLORS["member"], xlabel: str = "Trips",
                      save_path: Optional[str] = None, name_col: str = "station_name"):
    """Horizontal bars for a ranked list of stations (largest at the top)."""
    d = df.sort_values(value_col, ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bars = ax.barh([_short(n) for n in d[name_col]], d[value_col], color=color)
    for b in bars:
        v = b.get_width()
        label = f"{v:,.0f}" if v >= 100 else f"{v:,.1f}"
        ax.annotate(label, (v, b.get_y() + b.get_height() / 2), va="center", ha="left",
                    fontsize=8.5, xytext=(4, 0), textcoords="offset points")
    ax.set_xlabel(xlabel)
    ax.set_xlim(0, d[value_col].max() * 1.15)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="y", visible=False)
    return _finish(fig, title, subtitle, save_path)


def plot_net_flow(df: pd.DataFrame, n: int = 10, save_path: Optional[str] = None):
    """Diverging bars: stations that fill up (positive) vs empty out (negative).
    df columns: station_name, net_flow (arrivals - departures)"""
    top = df.nlargest(n, "net_flow")
    bottom = df.nsmallest(n, "net_flow")
    d = pd.concat([top, bottom]).sort_values("net_flow")
    fig, ax = plt.subplots(figsize=(9.5, 7))
    colors = [COLORS["positive"] if v > 0 else COLORS["negative"] for v in d["net_flow"]]
    ax.barh([_short(x) for x in d["station_name"]], d["net_flow"], color=colors)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Net flow = arrivals - departures (trips)")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="y", visible=False)
    return _finish(fig, "Which stations fill up and which empty out?",
                   f"Top {n} net receivers (green: bikes pile up) vs top {n} net senders "
                   "(red: bikes drain away, need rebalancing)", save_path)


def plot_station_map(df: pd.DataFrame, save_path: Optional[str] = None,
                     lat_bounds=(38.65, 39.25), lng_bounds=(-77.60, -76.70)):
    """Scatter of stations sized/coloured by departures. df: lat, lng, departures"""
    d = df.dropna(subset=["lat", "lng"])
    d = d[d["lat"].between(*lat_bounds) & d["lng"].between(*lng_bounds)].sort_values("departures")
    fig, ax = plt.subplots(figsize=(8.5, 8))
    sc = ax.scatter(d["lng"], d["lat"], c=d["departures"],
                    s=8 + 90 * d["departures"] / d["departures"].max(),
                    cmap="plasma", alpha=0.8, edgecolor="white", linewidth=0.3)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect(1 / np.cos(np.radians(38.9)))
    cb = fig.colorbar(sc, ax=ax, shrink=0.75, pad=0.01)
    cb.set_label("Departures")
    cb.formatter = mtick.FuncFormatter(_millions)
    cb.update_ticks()
    return _finish(fig, "Station map: where trips start",
                   "Bigger and brighter = more departures", save_path)


# --------------------------------------------------------------------------
# 5. Weather
# --------------------------------------------------------------------------
def plot_weather_bars(df: pd.DataFrame, label_col: str, value_col: str = "avg_trips_per_day",
                      title: str = "Average trips per day by weather", subtitle: Optional[str] = None,
                      save_path: Optional[str] = None, max_label: int = 46):
    """Horizontal bars of average daily trips per weather label (sorted)."""
    d = df.sort_values(value_col, ascending=True)
    best = d[value_col].max()
    fig, ax = plt.subplots(figsize=(10, max(3.6, 0.42 * len(d) + 1.6)))
    colors = [COLORS["member"] if v >= 0.85 * best else COLORS["neutral"] if v >= 0.5 * best
              else COLORS["highlight"] for v in d[value_col]]
    bars = ax.barh([_short(x, max_label) for x in d[label_col]], d[value_col], color=colors)
    for b in bars:
        ax.annotate(f"{b.get_width():,.0f}", (b.get_width(), b.get_y() + b.get_height() / 2),
                    va="center", ha="left", fontsize=9, xytext=(4, 0), textcoords="offset points")
    ax.set_xlabel("Average trips per day")
    ax.set_xlim(0, best * 1.12)
    ax.grid(axis="y", visible=False)
    return _finish(fig, title, subtitle, save_path)


def plot_temperature(df: pd.DataFrame, save_path: Optional[str] = None):
    """Scatter of daily trips vs mean temperature, coloured by rain, with trend.
    df columns: temp, trips, rainy (bool)"""
    d = df.dropna(subset=["temp", "trips"])
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    dry = d[~d["rainy"]]
    wet = d[d["rainy"]]
    ax.scatter(dry["temp"], dry["trips"], s=14, alpha=0.5, color=COLORS["casual"], label="No/low rain")
    ax.scatter(wet["temp"], wet["trips"], s=14, alpha=0.6, color=COLORS["member"], label="Rainy day")
    coef = np.polyfit(d["temp"], d["trips"], 2)
    xs = np.linspace(d["temp"].min(), d["temp"].max(), 100)
    ax.plot(xs, np.polyval(coef, xs), color="black", lw=2, label="Quadratic trend")
    r = np.corrcoef(d["temp"], d["trips"])[0, 1]
    ax.set_xlabel("Mean daily temperature (°C)")
    ax.set_ylabel("Trips per day")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.legend(frameon=False)
    return _finish(fig, "Temperature vs daily ridership",
                   f"Pearson r = {r:.2f}. Each dot is one day.", save_path)


# --------------------------------------------------------------------------
# 6. One-page summary dashboard
# --------------------------------------------------------------------------
def plot_dashboard(hourly: pd.DataFrame, weekday: pd.DataFrame, monthly: pd.DataFrame,
                   fleet: pd.DataFrame, top_stations: pd.DataFrame, weather: pd.DataFrame,
                   save_path: Optional[str] = None):
    """Six-panel executive summary.
    hourly: hour_of_day, number_of_trips | weekday: Day, Number_of_Trips
    monthly: year, month, trips | fleet: rideable_type, member_casual, number_of_rides
    top_stations: station_name, trip_count | weather: category, avg_trips_per_day"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 9.5))

    # hourly
    ax = axes[0, 0]
    h = hourly.copy()
    h["hour_of_day"] = h["hour_of_day"].astype(int)
    h = h.groupby("hour_of_day", as_index=False)["number_of_trips"].sum()
    top3 = set(h.nlargest(3, "number_of_trips")["hour_of_day"])
    ax.bar(h["hour_of_day"], h["number_of_trips"],
           color=[COLORS["highlight"] if x in top3 else COLORS["neutral"] for x in h["hour_of_day"]])
    ax.set_title("Trips by hour")
    ax.set_xticks(range(0, 24, 3))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.grid(axis="x", visible=False)

    # weekday
    ax = axes[0, 1]
    w = weekday.set_index("Day").reindex(DAY_ORDER)["Number_of_Trips"]
    ax.bar([d[:3] for d in w.index], w.values,
           color=[COLORS["highlight"] if v == w.max() else COLORS["positive"] if v == w.min()
                  else COLORS["neutral"] for v in w])
    ax.set_title("Trips by weekday")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.grid(axis="x", visible=False)

    # monthly seasonality
    ax = axes[0, 2]
    ys = sorted(monthly["year"].unique())
    cmap = plt.get_cmap("viridis")
    for i, y in enumerate(ys):
        s = monthly[monthly["year"] == y].sort_values("month")
        ax.plot(s["month"], s["trips"], marker="o", ms=3,
                color=cmap(i / max(len(ys) - 1, 1)), label=str(y))
    ax.set_title("Monthly trips by year")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(list("JFMAMJJASOND"))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.legend(loc="upper left", frameon=False, fontsize=8, ncol=2)

    # fleet mix
    ax = axes[1, 0]
    p = fleet.pivot_table(index="rideable_type", columns="member_casual",
                          values="number_of_rides", aggfunc="sum")
    p = p.loc[p.sum(axis=1).sort_values(ascending=False).index]
    x = np.arange(len(p))
    for i, rider in enumerate(["member", "casual"]):
        ax.bar(x + (i - 0.5) * 0.38, p[rider], 0.38, color=COLORS[rider], label=rider.title())
    ax.set_xticks(x)
    ax.set_xticklabels([BIKE_LABELS.get(i, i) for i in p.index])
    ax.set_title("Rides by bike and rider type")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)

    # top stations
    ax = axes[1, 1]
    t = top_stations.nlargest(8, "trip_count").sort_values("trip_count")
    ax.barh([_short(n, 28) for n in t["station_name"]], t["trip_count"], color=COLORS["member"])
    ax.set_title("Top 8 departure stations")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(_millions))
    ax.grid(axis="y", visible=False)

    # weather
    ax = axes[1, 2]
    wd = weather.sort_values("avg_trips_per_day")
    ax.barh(wd["category"], wd["avg_trips_per_day"], color=COLORS["casual"])
    ax.set_title("Average trips per day by weather")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="y", visible=False)

    fig.suptitle("City Bike-Share: Executive Dashboard", x=0.01, ha="left",
                 fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", facecolor="white")
    return fig
