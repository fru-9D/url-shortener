import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.base import TimestampMixin


class SuppressionReason(str, enum.Enum):
    bounce = "bounce"
    complaint = "complaint"


class EmailSuppression(Base, TimestampMixin):
    __tablename__ = "email_suppression"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # AES-256-GCM encrypted at the service layer (crypto.py); for ops/audit use.
    # The search hash cannot reverse to a plaintext address; ciphertext is needed for identification.
    email_ciphertext: Mapped[str] = mapped_column(String, nullable=False)
    email_search_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # unique via __table_args__
    reason: Mapped[SuppressionReason] = mapped_column(
        SAEnum(SuppressionReason, name="suppression_reason"), nullable=False
    )
    suppressed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("email_search_hash", name="uq_email_suppression_search_hash"),
    )

    def __repr__(self) -> str:
        return f"<EmailSuppression id={self.id} reason={self.reason}>"
