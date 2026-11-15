-- =============================================================================
-- 01 | DATA QUALITY AUDIT (read-only, run on the RAW tables)
-- Each query answers: "how bad is this problem?" before we clean it.
-- =============================================================================

-- A. Row count and duplicate ride_ids
SELECT COUNT(*)                                   AS total_rows,
       COUNT(DISTINCT ride_id)                    AS distinct_ride_ids,
       COUNT(*) - COUNT(DISTINCT ride_id)         AS duplicate_rows
FROM daily_rent_detail;

-- B. Missing values per column
SELECT SUM(ride_id            IS NULL) AS null_ride_id,
       SUM(rideable_type      IS NULL) AS null_bike_type,
       SUM(started_at         IS NULL) AS null_started_at,
       SUM(ended_at           IS NULL) AS null_ended_at,
       SUM(start_station_id   IS NULL) AS null_start_station_id,
       SUM(end_station_id     IS NULL) AS null_end_station_id,
       SUM(start_station_name IS NULL OR TRIM(start_station_name) = '') AS blank_start_station_name,
       SUM(end_station_name   IS NULL OR TRIM(end_station_name)   = '') AS blank_end_station_name,
       SUM(start_lat IS NULL OR start_lng IS NULL) AS null_start_coords,
       SUM(member_casual      IS NULL) AS null_rider_type
FROM daily_rent_detail;

-- C. Categorical values (look for typos, casing, unexpected labels)
SELECT rideable_type, COUNT(*) AS n FROM daily_rent_detail GROUP BY rideable_type ORDER BY n DESC;
SELECT member_casual, COUNT(*) AS n FROM daily_rent_detail GROUP BY member_casual ORDER BY n DESC;

-- D. Duration problems
SELECT COUNT(*)                                      AS total_trips,
       SUM(dur < 0)                                  AS negative_duration,
       SUM(dur >= 0 AND dur < 1)                     AS under_1_minute,
       SUM(dur > 1440)                               AS over_24_hours
FROM (SELECT (julianday(ended_at) - julianday(started_at)) * 1440.0 AS dur
      FROM daily_rent_detail);

-- E. Coordinates outside the Washington, DC metro area (or zero)
SELECT COUNT(*) AS bad_start_coords
FROM daily_rent_detail
WHERE start_lat IS NOT NULL
  AND (start_lat NOT BETWEEN 38.6 AND 39.3 OR start_lng NOT BETWEEN -77.7 AND -76.6);

-- F. Station names that share an id (inconsistent naming) and ids that share a name
SELECT COUNT(*) AS station_ids_with_multiple_names
FROM (SELECT start_station_id FROM daily_rent_detail
      WHERE start_station_id IS NOT NULL
      GROUP BY start_station_id HAVING COUNT(DISTINCT start_station_name) > 1);

-- G. Date range and timestamp format check
SELECT MIN(started_at) AS first_trip, MAX(started_at) AS last_trip,
       SUM(started_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]*') AS malformed_started_at
FROM daily_rent_detail;
