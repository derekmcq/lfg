from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(200), index=True, nullable=False)

    @property
    def platform_list(self) -> list[str]:
        return [p.strip() for p in self.platform.split(",") if p.strip()]
    description: Mapped[str] = mapped_column(Text, nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    author: Mapped["User"] = relationship("User", back_populates="posts")
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership", back_populates="post", cascade="all, delete-orphan"
    )
