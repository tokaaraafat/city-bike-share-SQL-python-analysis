# Data

The data is **not stored in this repository** (the trips file alone is ~1 GB).

**Source:** [Capital Bikeshare dataset on Kaggle](https://www.kaggle.com/datasets/taweilo/capital-bikeshare-dataset-202005202408) (May 2020 - Aug 2024). Check the Kaggle page for the dataset's terms of use.

| File | Description |
|---|---|
| `daily_rent_detail.csv` | One row per trip (~16.1 M rows) |
| `station_list.csv` | Station id and name |
| `usage_frequency.csv` | Daily pickups/dropoffs per station |
| `weather.csv` | Daily weather for Washington, DC |

Running `python -m src.build_database` (or the notebook) downloads the files with `kagglehub` and creates `data/city_bike_share.db` here. That file is git-ignored.

**Want to try the code without the download?** Generate a small *synthetic* dataset with the same schema:

```bash
python -m tests.make_sample_data --out data/sample_csvs --trips 200000
python -m src.build_database --data-dir data/sample_csvs --db data/sample.db
```

Synthetic data is random. Use it only to check that the pipeline runs, never to draw conclusions.
