from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_type: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(7), nullable=False)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="characters")
    stories = relationship("Story", back_populates="character", cascade="all, delete-orphan")
