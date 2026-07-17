from datetime import datetime

from pydantic import BaseModel, field_validator


class ObservationOut(BaseModel):
    id: int
    story_id: int
    message_id: int
    turn_number: int
    vocabulary_richness: int | None = None
    vocabulary_examples: str | None = None
    descriptive_ability: int | None = None
    descriptive_examples: str | None = None
    story_structure: int | None = None
    structure_note: str | None = None
    creativity_flags: str | None = None
    created_at: str | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = {"from_attributes": True}


class ObservationSummary(BaseModel):
    story_id: int
    total_turns: int
    avg_vocabulary_richness: float | None = None
    avg_descriptive_ability: float | None = None
    avg_story_structure: float | None = None
    all_creativity_flags: list[str] = []
    highlights: list[str] = []
