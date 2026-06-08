import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.base import TimestampMixin


class InviteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"
    cancelled = "cancelled"
    failed = "failed"


class InviteRole(str, enum.Enum):
    admin = "admin"
    editor = "editor"


class Invite(Base, TimestampMixin):
    __tablename__ = "invite"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="RESTRICT"), nullable=False
    )
    # AES-256-GCM encrypted at the service layer (crypto.py); per-row DEK sealed by AWS KMS.
    email_ciphertext: Mapped[str] = mapped_column(String, nullable=False)
    email_search_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[InviteRole] = mapped_column(SAEnum(InviteRole, name="invite_role"), nullable=False)
    inviter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[InviteStatus] = mapped_column(
        SAEnum(InviteStatus, name="invite_status"), nullable=False, default=InviteStatus.pending
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # unique via __table_args__
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="invites")  # noqa: F821
    inviter: Mapped["User | None"] = relationship(  # noqa: F821
        "User", back_populates="invites_sent", foreign_keys=[inviter_id]
    )

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_invite_token_hash"),
        # One pending invite per (workspace, email)
        Index(
            "uq_invite_pending_workspace_email",
            "workspace_id",
            "email_search_hash",
            unique=True,
            postgresql_where="status = 'pending'",
        ),
        Index("ix_invite_inviter_id", "inviter_id"),
        # Standalone workspace_id index for non-pending status queries (invite history, etc.)
        Index("ix_invite_workspace_id", "workspace_id"),
    )

    def __repr__(self) -> str:
        return f"<Invite id={self.id} status={self.status}>"
