import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.character import Character
from app.models.message import StoryMessage
from app.models.story import Story
from app.models.user import User
from app.schemas.message import StoryMessageOut
from app.schemas.story import StoryCreate, StoryOut, StoryUpdate, TurnRequest
from app.services import observation_service, story_service
from app.services.llm_service import LLMServiceError, get_llm_service

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("", response_model=list[StoryOut])
async def list_stories(
    character_id: int | None = None,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Story).join(Character).where(Character.user_id == current_user.id)
    if character_id:
        query = query.where(Story.character_id == character_id)
    if status:
        query = query.where(Story.status == status)
    query = query.order_by(Story.updated_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=StoryOut, status_code=status.HTTP_201_CREATED)
async def create_story(
    req: StoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify character belongs to user
    char = await db.get(Character, req.character_id)
    if not char or char.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")

    story = Story(
        character_id=req.character_id,
        theme=req.theme,
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)
    return story


@router.get("/{story_id}", response_model=StoryOut)
async def get_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    story = await _get_user_story(story_id, current_user, db)
    return story


@router.patch("/{story_id}", response_model=StoryOut)
async def update_story(
    story_id: int,
    req: StoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    story = await _get_user_story(story_id, current_user, db)
    if req.title is not None:
        story.title = req.title
    if req.status is not None:
        story.status = req.status
        if req.status == "completed":
            story.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(story)
    return story


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    story = await _get_user_story(story_id, current_user, db)
    await db.delete(story)
    await db.commit()


@router.get("/{story_id}/messages", response_model=list[StoryMessageOut])
async def get_story_messages(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_story(story_id, current_user, db)
    result = await db.execute(
        select(StoryMessage)
        .where(StoryMessage.story_id == story_id)
        .order_by(StoryMessage.turn_number, StoryMessage.id)
    )
    return result.scalars().all()


@router.post("/{story_id}/turn")
async def story_turn(
    story_id: int,
    req: TurnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The core endpoint: process a child's input and stream back the AI response."""
    story = await _get_user_story(story_id, current_user, db)

    if story.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="这个故事已经结束啦！")

    is_first_turn = (story.turn_count == 0)

    if not is_first_turn and not req.child_input.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="写下你的想法吧！")

    turn_number = story.turn_count + 1

    # Get character info for prompt (eager load, not via lazy relationship)
    char = await db.get(Character, story.character_id)

    # 1. Save child message (skip for first turn — AI initiates)
    child_msg = None
    if not is_first_turn:
        child_msg = await story_service.save_child_message(db, story_id, turn_number, req.child_input)

    # 2. Build message history
    messages = await story_service.get_story_messages(db, story_id)
    if not is_first_turn:
        messages.append({"role": "user", "content": req.child_input})
    else:
        # First turn: add a system-level trigger for the AI to start
        messages.append({"role": "user", "content": "请开始我们的故事吧！"})

    # 3. Content safety check (before LLM call, for instant feedback)
    from app.services.content_guard import check_content
    safety_result = None
    if req.child_input and req.child_input.strip():
        safety_result = check_content(req.child_input)

    # 4. LLM service with character + personality context
    llm = get_llm_service()

    async def event_generator():
        nonlocal safety_result
        narrative_parts = []
        question_text = ""
        observation_data = None
        ai_ending = False  # True when LLM sends ending event

        # Emit safety notice if triggered
        if safety_result and safety_result.is_flagged:
            yield f"event: safety_notice\ndata: {json.dumps({'message': safety_result.kind_message, 'level': safety_result.level}, ensure_ascii=False)}\n\n"

        try:
            async for chunk in llm.generate_turn(
                messages,
                character_name=char.nickname if char else "",
                character_type=char.avatar_type if char else "",
                personality=char.personality or "" if char else "",
                theme=story.theme or "",
                is_first_turn=is_first_turn,
            ):
                if chunk["type"] == "narrative_chunk":
                    narrative_parts.append(chunk["text"])
                    data = {"text": chunk["text"]}
                    # If LLM provided an image_prompt, use it; otherwise generate from text
                    img_prompt = chunk.get("image_prompt", "")
                    if not img_prompt and len(chunk["text"]) > 20:
                        from app.services.image_service import generate_image_prompt_from_narrative, generate_image_url
                        img_prompt = generate_image_prompt_from_narrative(chunk["text"])
                    if img_prompt:
                        from app.services.image_service import generate_image_url
                        data["image_url"] = generate_image_url(img_prompt)
                    yield f"event: narrative_chunk\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

                elif chunk["type"] == "ending":
                    ai_ending = True
                    narrative_parts.append(chunk["text"])
                    data = {"text": chunk["text"]}
                    from app.services.image_service import generate_image_prompt_from_narrative, generate_image_url
                    img_prompt = generate_image_prompt_from_narrative(chunk["text"])
                    data["image_url"] = generate_image_url(img_prompt)
                    yield f"event: ending\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

                elif chunk["type"] == "question":
                    question_text = chunk["text"]
                    yield f"event: question\ndata: {json.dumps({'text': question_text}, ensure_ascii=False)}\n\n"

                elif chunk["type"] == "observation":
                    observation_data = chunk["data"]
                    # Silently save — not sent to frontend

                elif chunk["type"] == "heartbeat":
                    yield f": heartbeat\n\n"

                elif chunk["type"] == "done":
                    narrative = "".join(narrative_parts)

                    # 4. Save AI message
                    ai_msg = await story_service.save_ai_message(
                        db, story_id, turn_number, narrative, question_text,
                        json.dumps({
                            "narrative": narrative,
                            "question": question_text,
                            "observation": observation_data,
                        }, ensure_ascii=False),
                    )

                    # 5. Save observation
                    # If LLM didn't provide observation, compute one programmatically
                    if not observation_data and child_msg and req.child_input and req.child_input.strip():
                        from app.services.llm_service import compute_observation
                        observation_data = compute_observation(req.child_input)

                    if observation_data and child_msg:
                        await observation_service.save_observation(
                            db, story_id, child_msg.id, turn_number, observation_data,
                        )

                    # 6. Update turn count (use explicit UPDATE to avoid ORM tracking issues)
                    await db.execute(
                        update(Story).where(Story.id == story_id).values(turn_count=turn_number)
                    )

                    # 7. Check if story should end: AI decides, soft cap at max_turns
                    is_ending = ai_ending or (turn_number >= settings.max_turns)
                    if is_ending:
                        await db.execute(
                            update(Story).where(Story.id == story_id).values(
                                status="completed",
                                completed_at=datetime.utcnow(),
                            )
                        )
                        # Build full_text
                        result = await db.execute(
                            select(StoryMessage)
                            .where(StoryMessage.story_id == story_id)
                            .order_by(StoryMessage.turn_number, StoryMessage.id)
                        )
                        all_msgs = result.scalars().all()
                        parts = []
                        for msg in all_msgs:
                            role_label = "【AI故事导演】" if msg.role == "ai" else "【小作家】"
                            parts.append(f"{role_label}\n{msg.content}")
                        await db.execute(
                            update(Story).where(Story.id == story_id).values(
                                full_text="\n\n".join(parts)
                            )
                        )

                    await db.commit()

                    yield f"event: done\ndata: {json.dumps({'message_id': ai_msg.id, 'turn_number': turn_number, 'is_ending': is_ending}, ensure_ascii=False)}\n\n"
                    return

        except LLMServiceError as e:
            yield f"event: error\ndata: {json.dumps({'message': f'故事导演去休息了，稍等一下哦~ {str(e)}'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps({'message': f'服务器出了点小问题: {str(e)[:200]}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _get_user_story(story_id: int, user: User, db: AsyncSession) -> Story:
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故事不存在")

    # Verify story belongs to user
    char = await db.get(Character, story.character_id)
    if not char or char.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故事不存在")

    return story
