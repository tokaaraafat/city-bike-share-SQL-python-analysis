-- =============================================================================
-- 02 | DATA CLEANING  ->  creates the table `trips_clean`
-- The raw table `daily_rent_detail` is never modified.
--
-- Rules applied
--   1. Remove duplicate rows (same ride_id): keep the first occurrence
--   2. Drop rows with missing ride_id / timestamps / unparseable timestamps
--   3. Standardise text: trim spaces, lower-case categories, blank -> NULL
--   4. Keep only valid categories (3 bike types, 2 rider types)
--   5. Null out coordinates outside the Washington, DC metro area
--   6. Keep trips lasting 1 minute to 24 hours (drops negatives, false starts,
--      and bikes that were never returned)
--   7. Add derived columns: duration_min, trip_date, year, month, hour, dow
-- =============================================================================

DROP TABLE IF EXISTS trips_clean;

CREATE TABLE trips_clean AS
SELECT
    t.ride_id,
    LOWER(TRIM(t.rideable_type))                              AS rideable_type,
    LOWER(TRIM(t.member_casual))                              AS member_casual,
    t.started_at,
    t.ended_at,
    t.start_station_id,
    CAST(t.end_station_id AS INTEGER)                         AS end_station_id,
    NULLIF(TRIM(t.start_station_name), '')                    AS start_station_name,
    NULLIF(TRIM(t.end_station_name), '')                      AS end_station_name,
    CASE WHEN t.start_lat BETWEEN 38.6 AND 39.3 AND t.start_lng BETWEEN -77.7 AND -76.6
         THEN t.start_lat END                                 AS start_lat,
    CASE WHEN t.start_lat BETWEEN 38.6 AND 39.3 AND t.start_lng BETWEEN -77.7 AND -76.6
         THEN t.start_lng END                                 AS start_lng,
    CASE WHEN t.end_lat BETWEEN 38.6 AND 39.3 AND t.end_lng BETWEEN -77.7 AND -76.6
         THEN t.end_lat END                                   AS end_lat,
    CASE WHEN t.end_lat BETWEEN 38.6 AND 39.3 AND t.end_lng BETWEEN -77.7 AND -76.6
         THEN t.end_lng END                                   AS end_lng,
    (julianday(t.ended_at) - julianday(t.started_at)) * 1440.0 AS duration_min,
    DATE(t.started_at)                                        AS trip_date,
    CAST(strftime('%Y', t.started_at) AS INTEGER)             AS year,
    CAST(strftime('%m', t.started_at) AS INTEGER)             AS month,
    CAST(strftime('%H', t.started_at) AS INTEGER)             AS hour,
    CAST(strftime('%w', t.started_at) AS INTEGER)             AS dow   -- 0 = Sunday
FROM daily_rent_detail AS t
WHERE t.rowid IN (                                   -- rule 1: de-duplicate
          SELECT MIN(rowid) FROM daily_rent_detail
          WHERE ride_id IS NOT NULL
          GROUP BY ride_id)
  AND t.started_at IS NOT NULL                       -- rule 2
  AND t.ended_at   IS NOT NULL
  AND julianday(t.started_at) IS NOT NULL
  AND julianday(t.ended_at)   IS NOT NULL
  AND LOWER(TRIM(t.rideable_type)) IN ('classic_bike', 'electric_bike', 'docked_bike')   -- rule 4
  AND LOWER(TRIM(t.member_casual)) IN ('member', 'casual')
  AND (julianday(t.ended_at) - julianday(t.started_at)) * 1440.0 BETWEEN 1 AND 1440;     -- rule 6

-- Post-clean validation (should show 0 problems)
-- SELECT COUNT(*) total, COUNT(DISTINCT ride_id) distinct_ids,
--        MIN(duration_min) min_dur, MAX(duration_min) max_dur FROM trips_clean;
