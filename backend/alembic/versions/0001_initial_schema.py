"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────────
    member_role = postgresql.ENUM("admin", "editor", name="member_role", create_type=False)
    member_role.create(op.get_bind(), checkfirst=True)

    invite_role = postgresql.ENUM("admin", "editor", name="invite_role", create_type=False)
    invite_role.create(op.get_bind(), checkfirst=True)

    invite_status = postgresql.ENUM(
        "pending", "accepted", "declined", "expired", "cancelled", "failed",
        name="invite_status", create_type=False,
    )
    invite_status.create(op.get_bind(), checkfirst=True)

    abuse_review_status = postgresql.ENUM(
        "pending_review", "whitelisted", "disabled", "hard_deleted",
        name="abuse_review_status", create_type=False,
    )
    abuse_review_status.create(op.get_bind(), checkfirst=True)

    suppression_reason = postgresql.ENUM(
        "bounce", "complaint", name="suppression_reason", create_type=False,
    )
    suppression_reason.create(op.get_bind(), checkfirst=True)

    # ── user ──────────────────────────────────────────────────────────────
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email_ciphertext", sa.Text(), nullable=False),
        sa.Column("email_search_hash", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_version", sa.Integer(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_user_email_search_hash", "user", ["email_search_hash"], unique=True)

    # ── workspace ─────────────────────────────────────────────────────────
    op.create_table(
        "workspace",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_workspace_owner_id", "workspace", ["owner_id"])

    # ── workspace_member ──────────────────────────────────────────────────
    op.create_table(
        "workspace_member",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Enum("admin", "editor", name="member_role"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_workspace_member_workspace_id", "workspace_member", ["workspace_id"])
    op.create_index("ix_workspace_member_user_id", "workspace_member", ["user_id"])
    # Partial unique: active user belongs to exactly one workspace
    op.create_index(
        "uq_workspace_member_user_active",
        "workspace_member",
        ["user_id"],
        unique=True,
        postgresql_where="removed_at IS NULL",
    )

    # ── invite ────────────────────────────────────────────────────────────
    op.create_table(
        "invite",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email_ciphertext", sa.Text(), nullable=False),
        sa.Column("email_search_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.Enum("admin", "editor", name="invite_role"), nullable=False),
        sa.Column("inviter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "accepted", "declined", "expired", "cancelled", "failed", name="invite_status"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inviter_id"], ["user.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("token_hash", name="uq_invite_token_hash"),
    )
    op.create_index("ix_invite_inviter_id", "invite", ["inviter_id"])
    op.create_index("ix_invite_workspace_id", "invite", ["workspace_id"])
    # Partial unique: one pending invite per (workspace, email)
    op.create_index(
        "uq_invite_pending_workspace_email",
        "invite",
        ["workspace_id", "email_search_hash"],
        unique=True,
        postgresql_where="status = 'pending'",
    )

    # ── link ──────────────────────────────────────────────────────────────
    op.create_table(
        "link",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("short_code", sa.String(32), nullable=False),
        sa.Column("destination_url", sa.String(2048), nullable=False),
        sa.Column("is_custom_slug", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"], ondelete="RESTRICT"),
    )
    # Partial unique: short_code unique among non-deleted links
    op.create_index(
        "uq_link_short_code_active",
        "link",
        ["short_code"],
        unique=True,
        postgresql_where="deleted_at IS NULL",
    )
    op.create_index("ix_link_workspace_created", "link", ["workspace_id", "created_at"])
    op.create_index("ix_link_owner_id", "link", ["owner_id"])
    op.create_index("ix_link_created_by_id", "link", ["created_by_id"])

    # ── click ─────────────────────────────────────────────────────────────
    op.create_table(
        "click",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("link_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("short_code", sa.String(32), nullable=False),
        sa.Column("country_code", sa.String(8), nullable=False),
        sa.Column("user_agent", sa.String(2048), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("referrer_host", sa.String(255), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["link_id"], ["link.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("event_id", name="uq_click_event_id"),
    )
    op.create_index("ix_click_workspace_clicked_at", "click", ["workspace_id", "clicked_at"])
    op.create_index("ix_click_link_clicked_at", "click", ["link_id", "clicked_at"])

    # ── password_reset_token ──────────────────────────────────────────────
    op.create_table(
        "password_reset_token",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),
    )
    op.create_index("ix_password_reset_token_user_id", "password_reset_token", ["user_id"])

    # ── email_verification_token ──────────────────────────────────────────
    op.create_table(
        "email_verification_token",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_email_verification_token_hash"),
    )
    op.create_index("ix_email_verification_token_user_id", "email_verification_token", ["user_id"])

    # ── email_suppression ─────────────────────────────────────────────────
    op.create_table(
        "email_suppression",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email_ciphertext", sa.Text(), nullable=False),
        sa.Column("email_search_hash", sa.String(64), nullable=False),
        sa.Column(
            "reason",
            sa.Enum("bounce", "complaint", name="suppression_reason"),
            nullable=False,
        ),
        sa.Column("suppressed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email_search_hash", name="uq_email_suppression_search_hash"),
    )

    # ── abuse_review ──────────────────────────────────────────────────────
    op.create_table(
        "abuse_review",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("link_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending_review", "whitelisted", "disabled", "hard_deleted", name="abuse_review_status"),
            nullable=False,
        ),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["link_id"], ["link.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["user.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_abuse_review_status", "abuse_review", ["status"])
    op.create_index("ix_abuse_review_link_flagged", "abuse_review", ["link_id", "flagged_at"])
    op.create_index("ix_abuse_review_workspace_id", "abuse_review", ["workspace_id"])
    op.create_index("ix_abuse_review_reviewer_id", "abuse_review", ["reviewer_id"])

    # ── mixpanel_dead_letter ──────────────────────────────────────────────
    op.create_table(
        "mixpanel_dead_letter",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_name", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("mixpanel_dead_letter")
    op.drop_table("abuse_review")
    op.drop_table("email_suppression")
    op.drop_table("email_verification_token")
    op.drop_table("password_reset_token")
    op.drop_table("click")
    op.drop_table("link")
    op.drop_table("invite")
    op.drop_table("workspace_member")
    op.drop_table("workspace")
    op.drop_table("user")

    for enum_name in [
        "member_role", "invite_role", "invite_status",
        "abuse_review_status", "suppression_reason",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
