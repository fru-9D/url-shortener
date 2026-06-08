import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text
from app.database import Base
from app.models.base import TimestampMixin


class MemberRole(str, enum.Enum):
    admin = "admin"
    editor = "editor"


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspace"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Relationships
    owner: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="owned_workspaces", foreign_keys=[owner_id]
    )
    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="workspace"
    )
    links: Mapped[list["Link"]] = relationship("Link", back_populates="workspace")  # noqa: F821
    invites: Mapped[list["Invite"]] = relationship("Invite", back_populates="workspace")  # noqa: F821
    clicks: Mapped[list["Click"]] = relationship("Click", back_populates="workspace")  # noqa: F821
    abuse_reviews: Mapped[list["AbuseReview"]] = relationship(  # noqa: F821
        "AbuseReview", back_populates="workspace"
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r}>"


class WorkspaceMember(Base, TimestampMixin):
    __tablename__ = "workspace_member"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[MemberRole] = mapped_column(SAEnum(MemberRole, name="member_role"), nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="workspace_memberships", foreign_keys=[user_id]
    )

    __table_args__ = (
        # Every active user belongs to exactly one workspace (PRD §Teams)
        Index(
            "uq_workspace_member_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
        Index("ix_workspace_member_workspace_id", "workspace_id"),
        Index("ix_workspace_member_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceMember user={self.user_id} workspace={self.workspace_id} role={self.role}>"
