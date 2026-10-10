"""initial_schema

Revision ID: a2a02956daa2
Revises: 
Create Date: 2026-09-23 17:33:14.613634

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'a2a02956daa2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # 1. stations
    if "stations" not in existing_tables:
        op.create_table(
            "stations",
            sa.Column("id", sa.String(length=100), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("city", sa.String(length=100), nullable=False),
            sa.Column("state", sa.String(length=100), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("agency", sa.String(length=100), nullable=True),
            sa.Column("source", sa.String(length=50), nullable=False, server_default="cpcb_caaqms"),
            sa.Column("ward_id", sa.String(length=100), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_stations_id", "stations", ["id"], unique=False)
        op.create_index("ix_stations_name", "stations", ["name"], unique=False)
        op.create_index("ix_stations_city", "stations", ["city"], unique=False)
        op.create_index("ix_stations_state", "stations", ["state"], unique=False)
        op.create_index("ix_stations_ward_id", "stations", ["ward_id"], unique=False)

    # 2. station_observations
    if "station_observations" not in existing_tables:
        op.create_table(
            "station_observations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("station_id", sa.String(length=100), sa.ForeignKey("stations.id"), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("pm25", sa.Float(), nullable=True),
            sa.Column("pm10", sa.Float(), nullable=True),
            sa.Column("no2", sa.Float(), nullable=True),
            sa.Column("so2", sa.Float(), nullable=True),
            sa.Column("co", sa.Float(), nullable=True),
            sa.Column("o3", sa.Float(), nullable=True),
            sa.Column("nh3", sa.Float(), nullable=True),
            sa.Column("aqi_in", sa.Float(), nullable=True),
            sa.Column("aqi_us", sa.Float(), nullable=True),
            sa.Column("primary_pollutant", sa.String(length=50), nullable=True),
            sa.Column("source", sa.String(length=50), nullable=False, server_default="cpcb_caaqms"),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("station_id", "timestamp", name="uix_station_obs_timestamp"),
        )
        op.create_index("ix_station_observations_id", "station_observations", ["id"], unique=False)
        op.create_index("ix_station_observations_station_id", "station_observations", ["station_id"], unique=False)
        op.create_index("ix_station_observations_timestamp", "station_observations", ["timestamp"], unique=False)
        op.create_index("ix_station_time", "station_observations", ["station_id", "timestamp"], unique=False)

    # 3. sensor_readings
    if "sensor_readings" not in existing_tables:
        op.create_table(
            "sensor_readings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("station_id", sa.String(length=100), nullable=False),
            sa.Column("timestamp", sa.String(length=100), nullable=False),
            sa.Column("pm25", sa.Float(), nullable=False),
            sa.Column("pm10", sa.Float(), nullable=False),
            sa.Column("temp", sa.Float(), nullable=False),
            sa.Column("humidity", sa.Float(), nullable=False),
            sa.Column("pressure", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_sensor_readings_id", "sensor_readings", ["id"], unique=False)
        op.create_index("ix_sensor_readings_station_id", "sensor_readings", ["station_id"], unique=False)

    # 4. forecasts
    if "forecasts" not in existing_tables:
        op.create_table(
            "forecasts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("horizon_h", sa.Integer(), nullable=False),
            sa.Column("points", sa.JSON(), nullable=False),
            sa.Column("intervals", sa.JSON(), nullable=False),
            sa.Column("ventilation_index", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_forecasts_id", "forecasts", ["id"], unique=False)

    # 5. attribution_results
    if "attribution_results" not in existing_tables:
        op.create_table(
            "attribution_results",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prediction_set", sa.JSON(), nullable=False),
            sa.Column("set_size", sa.Integer(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("probabilities", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_attribution_results_id", "attribution_results", ["id"], unique=False)

    # 6. enforcement_routes
    if "enforcement_routes" not in existing_tables:
        op.create_table(
            "enforcement_routes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("route_id", sa.String(length=100), nullable=False),
            sa.Column("stops", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_enforcement_routes_id", "enforcement_routes", ["id"], unique=False)
        op.create_index("ix_enforcement_routes_route_id", "enforcement_routes", ["route_id"], unique=True)

    # 7. roi_results
    if "roi_results" not in existing_tables:
        op.create_table(
            "roi_results",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("route_id", sa.String(length=100), nullable=False),
            sa.Column("exposure_reduction", sa.Float(), nullable=False),
            sa.Column("compliance_cost", sa.Float(), nullable=False),
            sa.Column("roi", sa.Float(), nullable=False),
            sa.Column("calculated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_roi_results_id", "roi_results", ["id"], unique=False)
        op.create_index("ix_roi_results_route_id", "roi_results", ["route_id"], unique=False)


def downgrade() -> None:
    op.drop_table("roi_results")
    op.drop_table("enforcement_routes")
    op.drop_table("attribution_results")
    op.drop_table("forecasts")
    op.drop_table("sensor_readings")
    op.drop_table("station_observations")
    op.drop_table("stations")
