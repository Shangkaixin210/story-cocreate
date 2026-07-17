from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.character import Character
from app.models.story import Story
from app.models.user import User
from app.services import talent_service

router = APIRouter(prefix="/talents", tags=["talents"])


@router.get("/{story_id}")
async def get_talent_profile(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the language talent profile for a completed story."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故事不存在")

    char = await db.get(Character, story.character_id)
    if not char or char.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故事不存在")

    profile = await talent_service.generate_talent_profile(db, story_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="无法生成天赋画像")

    # Return as dict (dataclass → dict with proper field names)
    return {
        "story_id": profile.story_id,
        "story_title": profile.story_title,
        "total_turns": profile.total_turns,
        "completed": profile.completed,
        "vocabulary_richness": profile.vocabulary_richness,
        "descriptive_ability": profile.descriptive_ability,
        "story_structure": profile.story_structure,
        "vocabulary_trend": profile.vocabulary_trend,
        "descriptive_trend": profile.descriptive_trend,
        "structure_trend": profile.structure_trend,
        "overall_level": profile.overall_level,
        "overall_score": profile.overall_score,
        "creativity_flags": profile.creativity_flags,
        "dominant_flag": profile.dominant_flag,
        "vocabulary_highlights": profile.vocabulary_highlights[:5],
        "descriptive_highlights": profile.descriptive_highlights[:5],
        "total_words_by_child": profile.total_words_by_child,
        "avg_words_per_turn": profile.avg_words_per_turn,
        "strengths": profile.strengths,
        "suggestions": profile.suggestions,
        "level_label": talent_service.LEVEL_DEFINITIONS.get(
            profile.overall_level, talent_service.LEVEL_DEFINITIONS["继续探索中"]
        )["label"],
        "level_description": talent_service.LEVEL_DEFINITIONS.get(
            profile.overall_level, talent_service.LEVEL_DEFINITIONS["继续探索中"]
        )["description"],
    }
