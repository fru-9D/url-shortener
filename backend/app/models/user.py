import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # AES-256-GCM encrypted at the service layer (crypto.py); per-row DEK sealed by AWS KMS.
    # The ORM stores opaque ciphertext — plaintext is never passed through SQLAlchemy.
    email_ciphertext: Mapped[str] = mapped_column(String, nullable=False)
    email_search_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(  # noqa: F821
        "WorkspaceMember", back_populates="user", foreign_keys="WorkspaceMember.user_id"
    )
    owned_workspaces: Mapped[list["Workspace"]] = relationship(  # noqa: F821
        "Workspace", back_populates="owner", foreign_keys="Workspace.owner_id"
    )
    owned_links: Mapped[list["Link"]] = relationship(  # noqa: F821
        "Link", back_populates="owner", foreign_keys="Link.owner_id"
    )
    created_links: Mapped[list["Link"]] = relationship(  # noqa: F821
        "Link", back_populates="creator", foreign_keys="Link.created_by_id"
    )
    invites_sent: Mapped[list["Invite"]] = relationship(  # noqa: F821
        "Invite", back_populates="inviter", foreign_keys="Invite.inviter_id"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(  # noqa: F821
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(  # noqa: F821
        "EmailVerificationToken", back_populates="user", cascade="all, delete-orphan"
    )
    abuse_reviews_assigned: Mapped[list["AbuseReview"]] = relationship(  # noqa: F821
        "AbuseReview", back_populates="reviewer", foreign_keys="AbuseReview.reviewer_id"
    )

    __table_args__ = (UniqueConstraint("email_search_hash", name="uq_user_email_search_hash"),)

    def __repr__(self) -> str:
        return f"<User id={self.id}>"
