import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.base import TimestampMixin


class Link(Base, TimestampMixin):
    __tablename__ = "link"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="RESTRICT"), nullable=False
    )
    # owner_id is mutable — reassigned to removing Admin on member removal
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    # created_by_id is immutable — original creator, preserved forever
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    short_code: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_custom_slug: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="links")  # noqa: F821
    owner: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="owned_links", foreign_keys=[owner_id]
    )
    creator: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="created_links", foreign_keys=[created_by_id]
    )
    # DB-level CASCADE handles orphan deletion; ORM cascade matches for session consistency
    clicks: Mapped[list["Click"]] = relationship(  # noqa: F821
        "Click", back_populates="link", cascade="all, delete-orphan"
    )
    abuse_reviews: Mapped[list["AbuseReview"]] = relationship(  # noqa: F821
        "AbuseReview", back_populates="link", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Partial unique: short_code globally unique among non-deleted links
        Index(
            "uq_link_short_code_active",
            "short_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_link_workspace_created", "workspace_id", "created_at"),
        Index("ix_link_owner_id", "owner_id"),
        Index("ix_link_created_by_id", "created_by_id"),
    )

    def __repr__(self) -> str:
        return f"<Link id={self.id} short_code={self.short_code!r}>"
