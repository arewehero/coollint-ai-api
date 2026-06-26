"""create recommendation domain tables

Revision ID: 0001_recommendation_domain
Revises:
Create Date: 2026-06-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_recommendation_domain"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lifestyle_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("primary_type", sa.String(length=30), nullable=False),
        sa.Column("secondary_type", sa.String(length=30), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=30), nullable=True),
        sa.Column("raw_ai_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_lifestyle_analysis_confidence"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_lifestyle_analysis_user_date", "lifestyle_analysis", ["user_id", "date"], unique=True)

    op.create_table(
        "recommendation_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("lifestyle_analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_estimated_saving_krw", sa.Integer(), server_default="0", nullable=False),
        sa.Column("monthly_estimated_saving_krw", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_energy_saving_kwh", sa.Numeric(8, 3), server_default="0", nullable=False),
        sa.Column("total_co2_reduction_kg", sa.Numeric(8, 3), server_default="0", nullable=False),
        sa.Column("cheer_message", sa.Text(), nullable=True),
        sa.Column("generated_by", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lifestyle_analysis_id"], ["lifestyle_analysis.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_recommendation_plans_user_date", "recommendation_plans", ["user_id", "date"], unique=True)

    op.create_table(
        "recommendation_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time_range", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("estimated_saving_krw", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_energy_saving_kwh", sa.Numeric(8, 3), server_default="0", nullable=False),
        sa.Column("estimated_co2_reduction_kg", sa.Numeric(8, 3), server_default="0", nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("priority_score", sa.Numeric(8, 3), server_default="0", nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["recommendation_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_recommendation_actions_plan", "recommendation_actions", ["plan_id", "sort_order"], unique=False)
    op.create_index("idx_recommendation_actions_user_date", "recommendation_actions", ["user_id", "date"], unique=False)

    op.create_table(
        "action_completion_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("saving_krw_delta", sa.Integer(), nullable=False),
        sa.Column("energy_kwh_delta", sa.Numeric(8, 3), nullable=False),
        sa.Column("co2_kg_delta", sa.Numeric(8, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["action_id"], ["recommendation_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_action_completion_logs_action", "action_completion_logs", ["action_id"], unique=False)
    op.create_index("idx_action_completion_logs_user_created_at", "action_completion_logs", ["user_id", "created_at"], unique=False)

    op.create_table(
        "saving_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("completed_action_count", sa.Integer(), nullable=False),
        sa.Column("total_saving_krw", sa.Integer(), nullable=False),
        sa.Column("total_energy_saving_kwh", sa.Numeric(10, 3), nullable=False),
        sa.Column("total_co2_reduction_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("monthly_projected_saving_krw", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_saving_summaries_user_period",
        "saving_summaries",
        ["user_id", "period_type", "period_start", "period_end"],
        unique=True,
    )
    op.create_index("idx_saving_summaries_user_period_start", "saving_summaries", ["user_id", "period_start"], unique=False)

    op.create_table(
        "ai_generation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=30), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("input_hash", sa.String(length=128), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_generation_logs_user_created_at", "ai_generation_logs", ["user_id", "created_at"], unique=False)
    op.create_index(
        "idx_ai_generation_logs_request_type_created_at",
        "ai_generation_logs",
        ["request_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_ai_generation_logs_request_type_created_at", table_name="ai_generation_logs")
    op.drop_index("idx_ai_generation_logs_user_created_at", table_name="ai_generation_logs")
    op.drop_table("ai_generation_logs")

    op.drop_index("idx_saving_summaries_user_period_start", table_name="saving_summaries")
    op.drop_index("uq_saving_summaries_user_period", table_name="saving_summaries")
    op.drop_table("saving_summaries")

    op.drop_index("idx_action_completion_logs_user_created_at", table_name="action_completion_logs")
    op.drop_index("idx_action_completion_logs_action", table_name="action_completion_logs")
    op.drop_table("action_completion_logs")

    op.drop_index("idx_recommendation_actions_user_date", table_name="recommendation_actions")
    op.drop_index("idx_recommendation_actions_plan", table_name="recommendation_actions")
    op.drop_table("recommendation_actions")

    op.drop_index("uq_recommendation_plans_user_date", table_name="recommendation_plans")
    op.drop_table("recommendation_plans")

    op.drop_index("uq_lifestyle_analysis_user_date", table_name="lifestyle_analysis")
    op.drop_table("lifestyle_analysis")
