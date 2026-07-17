from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint("vocabulary_richness >= 1 AND vocabulary_richness <= 5", name="ck_vocabulary"),
        CheckConstraint("descriptive_ability >= 1 AND descriptive_ability <= 5", name="ck_descriptive"),
        CheckConstraint("story_structure >= 1 AND story_structure <= 5", name="ck_structure"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id"), nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("story_messages.id"), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    vocabulary_richness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vocabulary_examples: Mapped[str | None] = mapped_column(Text, nullable=True)
    descriptive_ability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descriptive_examples: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_structure: Mapped[int | None] = mapped_column(Integer, nullable=True)
    structure_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    creativity_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    story = relationship("Story", back_populates="observations")
    message = relationship("StoryMessage", back_populates="observation")
