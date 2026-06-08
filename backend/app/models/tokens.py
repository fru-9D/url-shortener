import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.base import TimestampMixin


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_token"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # unique via __table_args__
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="password_reset_tokens"
    )

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),
        Index("ix_password_reset_token_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<PasswordResetToken id={self.id} user_id={self.user_id}>"


class EmailVerificationToken(Base, TimestampMixin):
    __tablename__ = "email_verification_token"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # unique via __table_args__
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="email_verification_tokens"
    )

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_email_verification_token_hash"),
        Index("ix_email_verification_token_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<EmailVerificationToken id={self.id} user_id={self.user_id}>"
