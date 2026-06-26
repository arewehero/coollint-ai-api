"""add score and weather tables

Revision ID: 0002_score_weather
Revises: 0001_recommendation_domain
Create Date: 2026-06-26 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_score_weather"
down_revision: Union[str, None] = "0001_recommendation_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- score_snapshots ---
    op.create_table(
        "score_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("morning_score", sa.Integer(), nullable=False),
        sa.Column("daytime_score", sa.Integer(), nullable=False),
        sa.Column("night_score", sa.Integer(), nullable=False),
        sa.Column("irregular_score", sa.Integer(), nullable=False),
        sa.Column("stay_home_score", sa.Integer(), nullable=False),
        sa.Column("outing_score", sa.Integer(), nullable=False),
        sa.Column("cooling_need_score", sa.Integer(), nullable=False),
        sa.Column("saving_priority_score", sa.Integer(), nullable=False),
        sa.Column("saving_opportunity_score", sa.Integer(), nullable=False),
        sa.Column("heat_gain_score", sa.Integer(), nullable=False),
        sa.Column("cooling_loss_score", sa.Integer(), nullable=False),
        sa.Column("ventilation_score", sa.Integer(), nullable=False),
        sa.Column("raw_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_score_snapshots_user_date", "score_snapshots", ["user_id", "date"], unique=True)

    # --- weather_snapshots ---
    op.create_table(
        "weather_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("region_name", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=50), server_default="openweathermap", nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_weather_snapshots_date_expires_at", "weather_snapshots", ["date", "expires_at"], unique=False)

    # --- weather_time_blocks ---
    op.create_table(
        "weather_time_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weather_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time_range", sa.String(length=20), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature", sa.Numeric(5, 2), nullable=False),
        sa.Column("feels_like", sa.Numeric(5, 2), nullable=False),
        sa.Column("humidity", sa.Integer(), nullable=False),
        sa.Column("rain", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("uv_index", sa.Numeric(4, 2), nullable=True),
        sa.Column("heat_alert", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("weather_risk_score", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["weather_snapshot_id"], ["weather_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_weather_time_blocks_snapshot_time_range",
        "weather_time_blocks",
        ["weather_snapshot_id", "time_range"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_weather_time_blocks_snapshot_time_range", table_name="weather_time_blocks")
    op.drop_table("weather_time_blocks")

    op.drop_index("idx_weather_snapshots_date_expires_at", table_name="weather_snapshots")
    op.drop_table("weather_snapshots")

    op.drop_index("uq_score_snapshots_user_date", table_name="score_snapshots")
    op.drop_table("score_snapshots")
