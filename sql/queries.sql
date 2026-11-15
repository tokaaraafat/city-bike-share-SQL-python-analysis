-- =============================================================================
-- City Bike-Share: SQL queries (SQLite)
-- Run order: build the database first with `python -m src.build_database`
-- (creates the raw tables + the cleaned table `trips_clean`).
-- Question numbers match the original project brief.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Data-quality audit on the RAW table
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*)                          AS total_trips,
    SUM(dur < 0)                      AS negative_duration,
    SUM(dur >= 0 AND dur < 1)         AS under_1_minute,
    SUM(dur > 1440)                   AS over_24_hours,
    SUM(start_station_id IS NULL)     AS missing_start_station,
    SUM(end_station_id   IS NULL)     AS missing_end_station
FROM (
    SELECT (julianday(ended_at) - julianday(started_at)) * 1440.0 AS dur,
           start_station_id,
           end_station_id
    FROM daily_rent_detail
);

-- -----------------------------------------------------------------------------
-- Q2. Rides by bike type and rider type
-- -----------------------------------------------------------------------------
SELECT rideable_type, member_casual, COUNT(*) AS number_of_rides
FROM trips_clean
GROUP BY rideable_type, member_casual
ORDER BY rideable_type, member_casual;

-- -----------------------------------------------------------------------------
-- Q3. Ten longest trips in July 2024 (cleaned: capped at 24 h)
-- -----------------------------------------------------------------------------
SELECT ride_id, started_at, ended_at, CAST(duration_min AS INTEGER) AS duration_minutes
FROM trips_clean
WHERE year = 2024 AND month = 7
ORDER BY duration_min DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- Q5. Total trips and average duration, by month of 2024
-- -----------------------------------------------------------------------------
SELECT month,
       COUNT(*)                    AS total_trips,
       ROUND(AVG(duration_min), 2) AS avg_trip_duration_min
FROM trips_clean
WHERE year = 2024
GROUP BY month
ORDER BY month;

-- -----------------------------------------------------------------------------
-- Q6. Trips per start hour (0-23)
-- -----------------------------------------------------------------------------
SELECT hour AS hour_of_day, COUNT(*) AS number_of_trips
FROM trips_clean
GROUP BY hour
ORDER BY number_of_trips DESC;

-- -----------------------------------------------------------------------------
-- Q7. Trips per day of week
-- -----------------------------------------------------------------------------
SELECT CASE dow
           WHEN 0 THEN 'Sunday'   WHEN 1 THEN 'Monday'   WHEN 2 THEN 'Tuesday'
           WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
           WHEN 6 THEN 'Saturday'
       END AS day_of_week,
       COUNT(*) AS number_of_trips
FROM trips_clean
GROUP BY dow
ORDER BY number_of_trips DESC;

-- -----------------------------------------------------------------------------
-- Q10. Top 10 stations by departures
-- -----------------------------------------------------------------------------
SELECT MAX(start_station_name) AS station_name, COUNT(*) AS trip_count
FROM trips_clean
WHERE start_station_id IS NOT NULL
GROUP BY start_station_id
ORDER BY trip_count DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- Q11. Net flow per station (arrivals - departures)
--      positive = station fills up, negative = station empties out
-- -----------------------------------------------------------------------------
SELECT f.station_id,
       COALESCE(s.station_name, CAST(f.station_id AS TEXT)) AS station_name,
       SUM(f.departures)                                    AS departures,
       SUM(f.arrivals)                                      AS arrivals,
       SUM(f.arrivals) - SUM(f.departures)                  AS net_flow
FROM (
    SELECT start_station_id AS station_id, COUNT(*) AS departures, 0 AS arrivals
    FROM trips_clean
    WHERE start_station_id IS NOT NULL
    GROUP BY start_station_id

    UNION ALL

    SELECT end_station_id AS station_id, 0 AS departures, COUNT(*) AS arrivals
    FROM trips_clean
    WHERE end_station_id IS NOT NULL
    GROUP BY end_station_id
) AS f
LEFT JOIN (SELECT station_id, MAX(station_name) AS station_name
           FROM station_list GROUP BY station_id) AS s
       ON s.station_id = f.station_id
GROUP BY f.station_id
ORDER BY net_flow DESC;

-- -----------------------------------------------------------------------------
-- Q12. Members vs casual riders: trips and average duration (cleaned)
-- -----------------------------------------------------------------------------
SELECT member_casual,
       COUNT(*)                    AS number_of_trips,
       ROUND(AVG(duration_min), 2) AS avg_trip_duration_min
FROM trips_clean
GROUP BY member_casual;

-- -----------------------------------------------------------------------------
-- Q16. Does weather matter? Average trips per day by weather condition
-- -----------------------------------------------------------------------------
SELECT w.conditions,
       COUNT(*)                         AS days,
       ROUND(AVG(d.daily_trips), 0)     AS avg_trips_per_day
FROM (SELECT trip_date, COUNT(*) AS daily_trips
      FROM trips_clean
      GROUP BY trip_date) AS d
JOIN weather AS w ON d.trip_date = w.datetime
GROUP BY w.conditions
ORDER BY avg_trips_per_day DESC;
