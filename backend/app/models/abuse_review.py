import uuid
import enum
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.base import TimestampMixin


class AbuseReviewStatus(str, enum.Enum):
    pending_review = "pending_review"
    whitelisted = "whitelisted"
    disabled = "disabled"
    hard_deleted = "hard_deleted"


class AbuseReview(Base, TimestampMixin):
    __tablename__ = "abuse_review"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("link.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="RESTRICT"), nullable=False
    )
    # Nullable until a reviewer acts
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[AbuseReviewStatus] = mapped_column(
        SAEnum(AbuseReviewStatus, name="abuse_review_status"),
        nullable=False,
        default=AbuseReviewStatus.pending_review,
    )
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    link: Mapped["Link"] = relationship("Link", back_populates="abuse_reviews")  # noqa: F821
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="abuse_reviews")  # noqa: F821
    reviewer: Mapped["User | None"] = relationship(  # noqa: F821
        "User", back_populates="abuse_reviews_assigned", foreign_keys=[reviewer_id]
    )

    __table_args__ = (
        Index("ix_abuse_review_status", "status"),
        Index("ix_abuse_review_link_flagged", "link_id", "flagged_at"),
        Index("ix_abuse_review_workspace_id", "workspace_id"),
        Index("ix_abuse_review_reviewer_id", "reviewer_id"),
    )

    def __repr__(self) -> str:
        return f"<AbuseReview id={self.id} status={self.status}>"
