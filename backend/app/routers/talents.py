from dataclasses import asdict

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
    """Get three independent 100-point talent reports plus language progress."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故事不存在")

    char = await db.get(Character, story.character_id)
    if not char or char.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故事不存在")

    p = await talent_service.generate_talent_profile(db, story_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="无法生成天赋画像")

    return asdict(p)
