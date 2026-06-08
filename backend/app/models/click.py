import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class Click(Base):
    """CLICK is append-only — no updated_at, no TimestampMixin."""
    __tablename__ = "click"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("link.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="RESTRICT"), nullable=False
    )
    # event_id is the stable idempotency key emitted by the redirect service
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # unique via __table_args__
    # Denormalized — redirect service has LINK row in hand at click-emission time
    short_code: Mapped[str] = mapped_column(String(32), nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, default="Unknown")
    user_agent: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    referrer_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    link: Mapped["Link"] = relationship("Link", back_populates="clicks")  # noqa: F821
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="clicks")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("event_id", name="uq_click_event_id"),
        Index("ix_click_workspace_clicked_at", "workspace_id", "clicked_at"),
        Index("ix_click_link_clicked_at", "link_id", "clicked_at"),
    )

    def __repr__(self) -> str:
        return f"<Click id={self.id} link_id={self.link_id}>"
