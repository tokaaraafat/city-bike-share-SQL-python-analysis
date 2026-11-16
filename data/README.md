# Data

**Source:** [Capital Bikeshare dataset on Kaggle](https://www.kaggle.com/datasets/taweilo/capital-bikeshare-dataset-202005202408) (May 2020 – Aug 2024).

| File | Description |
|---|---|
| `daily_rent_detail.csv` | One row per trip (~16.1 M rows) |
| `station_list.csv` | Station id and name |
| `usage_frequency.csv` | Daily pickups and dropoffs per station |
| `weather.csv` | Daily weather for Washington, DC |

The files are downloaded with `kagglehub` and loaded into `data/city_bike_share.db` by the notebook or by `python -m src.build_database`. The database is git-ignored.

To try the pipeline on a small synthetic dataset with the same schema:

```bash
python -m tests.make_sample_data --out data/sample_csvs --trips 200000
python -m src.build_database --data-dir data/sample_csvs --db data/sample.db
```
