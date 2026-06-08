import uuid
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base
from app.models.base import TimestampMixin


class MixpanelDeadLetter(Base, TimestampMixin):
    __tablename__ = "mixpanel_dead_letter"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable — account-level events (password_reset_requested) have no workspace context
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    def __repr__(self) -> str:
        return f"<MixpanelDeadLetter id={self.id} event={self.event_name!r}>"
