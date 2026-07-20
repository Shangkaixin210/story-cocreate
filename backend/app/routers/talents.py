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
    """Get the 5-dimension language talent profile for a completed story."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故事不存在")

    char = await db.get(Character, story.character_id)
    if not char or char.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故事不存在")

    p = await talent_service.generate_talent_profile(db, story_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="无法生成天赋画像")

    return {
        "story_id": p.story_id,
        "story_title": p.story_title,
        "total_turns": p.total_turns,
        "age_group": p.age_group,
        "completed": p.completed,

        # 5 dimensions
        "avg_vocabulary_semantic": p.avg_vocabulary_semantic,
        "avg_sentence_fluency": p.avg_sentence_fluency,
        "avg_narrative_completeness": p.avg_narrative_completeness,
        "avg_character_empathy": p.avg_character_empathy,
        "avg_creative_initiative": p.avg_creative_initiative,
        "overall_score": p.overall_score,

        # Trends
        "vocab_trend": p.vocab_trend,
        "fluency_trend": p.fluency_trend,
        "narrative_trend": p.narrative_trend,
        "empathy_trend": p.empathy_trend,
        "initiative_trend": p.initiative_trend,

        # Level
        "overall_level": p.overall_level,
        "level_label": p.level_label,
        "level_description": p.level_description,
        "talent_tags": p.talent_tags,

        # Highlights
        "semantic_highlights": p.semantic_highlights[:5],
        "empathy_highlights": p.empathy_highlights[:5],
        "initiative_highlights": p.initiative_highlights[:5],

        # Stats
        "total_words": p.total_words,
        "avg_words_per_turn": p.avg_words_per_turn,

        # Feedback
        "strengths": p.strengths,
        "suggestions": p.suggestions,
    }
