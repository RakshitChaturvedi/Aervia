-- ==========================================================
-- Aervia: PostgreSQL & TimescaleDB Production Migration
-- Architecture: Enterprise Time-Series Hypertables,
-- Columnar zstd Compression, Retention Policies & Continuous Aggregates
-- ==========================================================

-- 1. Enable TimescaleDB extension if available in PostgreSQL
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 2. Physical Ambient Air Quality Monitoring Stations (CAAQMS & OpenAQ)
CREATE TABLE IF NOT EXISTS stations (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    agency VARCHAR(100),
    source VARCHAR(50) NOT NULL DEFAULT 'cpcb_caaqms',
    ward_id VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS ix_stations_city ON stations (city);
CREATE INDEX IF NOT EXISTS ix_stations_ward_id ON stations (ward_id);
CREATE INDEX IF NOT EXISTS ix_stations_agency ON stations (agency);

-- 3. Time-Series Station Observations
CREATE TABLE IF NOT EXISTS station_observations (
    station_id VARCHAR(100) NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    pm25 DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    no2 DOUBLE PRECISION,
    so2 DOUBLE PRECISION,
    co DOUBLE PRECISION,
    o3 DOUBLE PRECISION,
    nh3 DOUBLE PRECISION,
    aqi_in DOUBLE PRECISION,
    aqi_us DOUBLE PRECISION,
    primary_pollutant VARCHAR(50),
    source VARCHAR(50) NOT NULL DEFAULT 'cpcb_caaqms',
    raw_payload JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    PRIMARY KEY (station_id, timestamp)
);

CREATE INDEX IF NOT EXISTS ix_station_observations_time ON station_observations (timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_station_observations_station_time ON station_observations (station_id, timestamp DESC);

-- 4. IoT Fleet Telemetry (ESP32 Mobile/Ward Sensors)
CREATE TABLE IF NOT EXISTS sensor_readings (
    id BIGSERIAL,
    station_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    pm25 DOUBLE PRECISION NOT NULL,
    pm10 DOUBLE PRECISION NOT NULL,
    temp DOUBLE PRECISION NOT NULL,
    humidity DOUBLE PRECISION NOT NULL,
    pressure DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    PRIMARY KEY (station_id, timestamp, id)
);

CREATE INDEX IF NOT EXISTS ix_sensor_readings_station_time ON sensor_readings (station_id, timestamp DESC);

-- 5. Turn into TimescaleDB Hypertables (7-Day Chunk Intervals)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        -- Create hypertable for station_observations
        PERFORM create_hypertable(
            'station_observations',
            'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );
        RAISE NOTICE 'Hypertable created for station_observations (7-day intervals).';

        -- Create hypertable for sensor_readings
        PERFORM create_hypertable(
            'sensor_readings',
            'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );
        RAISE NOTICE 'Hypertable created for sensor_readings (7-day intervals).';
    ELSE
        RAISE NOTICE 'TimescaleDB extension not present; standard PostgreSQL tables will be used.';
    END IF;
END $$;

-- 6. Native Columnar Chunk Compression Policies (Older than 7 days)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        -- Enable compression on station_observations
        ALTER TABLE station_observations SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'station_id',
            timescaledb.compress_orderby = 'timestamp DESC'
        );
        PERFORM add_compression_policy('station_observations', INTERVAL '7 days', if_not_exists => TRUE);
        RAISE NOTICE 'Compression policy attached to station_observations (7 days).';

        -- Enable compression on sensor_readings
        ALTER TABLE sensor_readings SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'station_id',
            timescaledb.compress_orderby = 'timestamp DESC'
        );
        PERFORM add_compression_policy('sensor_readings', INTERVAL '7 days', if_not_exists => TRUE);
        RAISE NOTICE 'Compression policy attached to sensor_readings (7 days).';
    END IF;
END $$;

-- 7. Data Retention Policies (Purge raw high-frequency telemetry older than 1 year)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM add_retention_policy('station_observations', INTERVAL '365 days', if_not_exists => TRUE);
        PERFORM add_retention_policy('sensor_readings', INTERVAL '365 days', if_not_exists => TRUE);
        RAISE NOTICE 'Retention policy applied: 365 days retention for raw telemetry.';
    END IF;
END $$;

-- 8. Continuous Aggregates for Instant Sub-Millisecond Analytics Queries
-- Hourly Aggregate View
CREATE MATERIALIZED VIEW IF NOT EXISTS station_observations_hourly
WITH (timescaledb.continuous) AS
SELECT
    station_id,
    time_bucket('1 hour', timestamp) AS bucket,
    AVG(pm25) AS avg_pm25,
    MIN(pm25) AS min_pm25,
    MAX(pm25) AS max_pm25,
    AVG(pm10) AS avg_pm10,
    AVG(no2) AS avg_no2,
    AVG(so2) AS avg_so2,
    AVG(co) AS avg_co,
    AVG(o3) AS avg_o3,
    AVG(nh3) AS avg_nh3,
    AVG(aqi_in) AS avg_aqi_in,
    AVG(aqi_us) AS avg_aqi_us,
    COUNT(*) AS sample_count
FROM station_observations
GROUP BY station_id, bucket
WITH NO DATA;

-- Daily Aggregate View
CREATE MATERIALIZED VIEW IF NOT EXISTS station_observations_daily
WITH (timescaledb.continuous) AS
SELECT
    station_id,
    time_bucket('1 day', timestamp) AS bucket,
    AVG(pm25) AS avg_pm25,
    MIN(pm25) AS min_pm25,
    MAX(pm25) AS max_pm25,
    AVG(pm10) AS avg_pm10,
    AVG(no2) AS avg_no2,
    AVG(so2) AS avg_so2,
    AVG(co) AS avg_co,
    AVG(o3) AS avg_o3,
    AVG(nh3) AS avg_nh3,
    AVG(aqi_in) AS avg_aqi_in,
    AVG(aqi_us) AS avg_aqi_us,
    COUNT(*) AS sample_count
FROM station_observations
GROUP BY station_id, bucket
WITH NO DATA;

-- Automated Refresh Policies for Continuous Aggregates
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        -- Hourly rollup policy: runs every 1 hour, covers last 3 days
        PERFORM add_continuous_aggregate_policy(
            'station_observations_hourly',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour',
            if_not_exists => TRUE
        );

        -- Daily rollup policy: runs once daily, covers last 30 days
        PERFORM add_continuous_aggregate_policy(
            'station_observations_daily',
            start_offset => INTERVAL '30 days',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
        RAISE NOTICE 'Continuous aggregate refresh policies scheduled successfully.';
    END IF;
END $$;
