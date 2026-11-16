"""
Generate a small synthetic dataset with the same schema as the Kaggle files,
for trying the pipeline without the full download.

    python -m tests.make_sample_data --out data/sample_csvs --trips 200000
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd


def make_sample(out_dir: str, n_trips: int = 200_000, n_stations: int = 150, seed: int = 7) -> str:
    rng = np.random.default_rng(seed)
    os.makedirs(out_dir, exist_ok=True)

    # ---- stations -------------------------------------------------------
    ids = np.arange(31000, 31000 + n_stations)
    names = [f"{rng.integers(1, 30)}th & {chr(65 + i % 26)} St NW #{i}" for i in range(n_stations)]
    stations = pd.DataFrame({"station_id": ids, "station_name": names})
    stations.to_csv(os.path.join(out_dir, "station_list.csv"), index=False)
    lat = 38.90 + rng.normal(0, 0.04, n_stations)
    lng = -77.03 + rng.normal(0, 0.05, n_stations)
    popularity = rng.pareto(1.5, n_stations) + 0.2
    popularity /= popularity.sum()

    # ---- weather --------------------------------------------------------
    days = pd.date_range("2020-05-01", "2024-08-31", freq="D")
    doy = days.dayofyear.values
    temp = 14 + 12 * np.sin((doy - 110) / 365 * 2 * np.pi) + rng.normal(0, 3, len(days))
    precip = np.where(rng.random(len(days)) < 0.3, rng.exponential(6, len(days)), 0.0)
    snow = np.where((temp < 1) & (precip > 0), precip, 0.0)
    cloud = rng.random(len(days))
    cond = []
    for t, p, s, c in zip(temp, precip, snow, cloud):
        if s > 0:
            cond.append("Snow, Rain, Overcast")
        elif p > 0:
            cond.append("Rain, Overcast" if c > 0.5 else "Rain, Partially cloudy")
        else:
            cond.append("Clear" if c < 0.4 else "Partially cloudy" if c < 0.75 else "Overcast")
    weather = pd.DataFrame({
        "name": "Washington,DC,USA", "datetime": days.strftime("%Y-%m-%d"),
        "tempmax": temp + 4, "tempmin": temp - 4, "temp": temp.round(1),
        "precip": precip.round(2), "snow": snow.round(2),
        "windspeed": rng.uniform(5, 30, len(days)).round(1), "conditions": cond})
    weather.to_csv(os.path.join(out_dir, "weather.csv"), index=False)

    # ---- trips ----------------------------------------------------------
    # day weights follow temperature and weather so the relationships are visible
    w = np.clip(0.4 + (temp + 5) / 30, 0.05, None) * np.where(precip > 2, 0.6, 1) * np.where(snow > 0, 0.3, 1)
    w = w / w.sum()
    day_idx = rng.choice(len(days), n_trips, p=w)
    hour_p = np.array([1, 1, .5, .4, .4, 1, 3, 8, 12, 7, 5, 5, 6, 6, 6, 7, 9, 12, 10, 6, 4, 3, 2, 1.5])
    hour = rng.choice(24, n_trips, p=hour_p / hour_p.sum())
    secs = rng.integers(0, 3600, n_trips)
    start = days[day_idx] + pd.to_timedelta(hour, unit="h") + pd.to_timedelta(secs, unit="s")
    member = rng.random(n_trips) < 0.6
    dur = np.where(member, rng.lognormal(1.9, 0.6, n_trips), rng.lognormal(2.7, 0.8, n_trips))  # minutes
    r = rng.random(n_trips)
    dur = np.where(r < 0.005, -rng.uniform(1, 600, n_trips), dur)          # bad rows: negative
    dur = np.where((r >= 0.005) & (r < 0.01), rng.uniform(1500, 3000, n_trips), dur)  # >24h
    dur = np.where((r >= 0.01) & (r < 0.015), rng.uniform(0, 0.9, n_trips), dur)     # <1 min
    end = start + pd.to_timedelta(dur, unit="m")
    bike = np.where(start.year >= 2021, rng.choice(["classic_bike", "electric_bike"], n_trips, p=[.65, .35]),
                    rng.choice(["docked_bike", "classic_bike"], n_trips, p=[.7, .3]))
    s_idx = rng.choice(n_stations, n_trips, p=popularity)
    e_idx = rng.choice(n_stations, n_trips, p=np.roll(popularity, 3))
    end_id = ids[e_idx].astype(float)
    end_id[rng.random(n_trips) < 0.02] = np.nan
    fmt = np.where(start.year >= 2024, "ms", "s")
    started = pd.Series(start.strftime("%Y-%m-%d %H:%M:%S"))
    ended = pd.Series(end.strftime("%Y-%m-%d %H:%M:%S"))
    ms = fmt == "ms"
    started[ms] = started[ms] + ".123"
    ended[ms] = ended[ms] + ".456"
    trips = pd.DataFrame({
        "ride_id": [f"{i:016X}" for i in range(n_trips)], "rideable_type": bike,
        "started_at": started, "ended_at": ended,
        "start_station_name": np.array(names)[s_idx], "start_station_id": ids[s_idx],
        "end_station_name": np.array(names)[e_idx], "end_station_id": end_id,
        "start_lat": lat[s_idx], "start_lng": lng[s_idx],
        "end_lat": lat[e_idx], "end_lng": lng[e_idx],
        "member_casual": np.where(member, "member", "casual")})
    trips.to_csv(os.path.join(out_dir, "daily_rent_detail.csv"), index=False)

    # ---- usage frequency (not used by the notebook's new section) --------
    uf = pd.DataFrame({"date": weather["datetime"].iloc[:50].repeat(3).values,
                       "station_name": np.tile(names[:3], 50),
                       "pickup_counts": rng.integers(1, 20, 150),
                       "dropoff_counts": rng.integers(1, 20, 150).astype(float)})
    uf.to_csv(os.path.join(out_dir, "usage_frequency.csv"), index=False)
    return out_dir


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/sample_csvs")
    ap.add_argument("--trips", type=int, default=200_000)
    a = ap.parse_args()
    print("wrote", make_sample(a.out, a.trips))
