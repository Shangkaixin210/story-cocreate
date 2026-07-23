"""Generate the standardized three-channel talent report.

Only observations attached to genuine child messages are used. Historical
stories belonging to the same account provide the persistent progress memory.
"""

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.models.message import StoryMessage
from app.models.observation import Observation
from app.models.story import Story


@dataclass
class TalentProfile:
    story_id: int
    story_title: str
    total_turns: int
    age_group: str
    completed: bool
    language: dict = field(default_factory=dict)
    empathy: dict = field(default_factory=dict)
    imagination: dict = field(default_factory=dict)
    growth_memory: dict = field(default_factory=dict)
    highlights: list[str] = field(default_factory=list)
    total_words: int = 0
    avg_words_per_turn: float = 0.0
    strengths: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


RUBRIC_KEYS = (
    "language_causal_logic", "language_plot_memory", "language_vocabulary",
    "language_detail", "language_character_voice", "language_initiative",
    "empathy_emotion", "empathy_perspective", "empathy_prosocial",
    "empathy_conflict", "imagination_character", "imagination_setting",
    "imagination_rules", "imagination_side_plot",
)


def _is_system_ending_request(text: str) -> bool:
    normalized = "".join(text.split())
    return "请从刚才的情节继续" in normalized and "完整的大结局" in normalized


def _raw(observation: Observation) -> dict:
    try:
        value = json.loads(observation.raw_observation or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _rubric_value(observation: Observation, key: str) -> float:
    data = _raw(observation)
    if key in data:
        try:
            return float(max(0, min(5, float(data[key]))))
        except (TypeError, ValueError):
            pass

    vocab = float(observation.vocabulary_semantic or 1)
    fluency = float(observation.sentence_fluency or 1)
    narrative = float(observation.narrative_completeness or 1)
    empathy = float(observation.character_empathy or 1)
    initiative = float(observation.creative_initiative or 1)
    legacy = {
        "language_causal_logic": narrative,
        "language_plot_memory": max(0, narrative - 1),
        "language_vocabulary": vocab,
        "language_detail": max(0, (vocab + fluency) / 2 - 1),
        "language_character_voice": empathy,
        "language_initiative": initiative,
        "empathy_emotion": empathy,
        "empathy_perspective": max(0, empathy - 1),
        "empathy_prosocial": max(0, empathy - 1),
        "empathy_conflict": max(0, empathy - 1),
        "imagination_character": initiative,
        "imagination_setting": max(0, initiative - 1),
        "imagination_rules": max(0, initiative - 1),
        "imagination_side_plot": max(0, initiative - 1),
    }
    return legacy[key]


def _averages(observations: list[Observation]) -> dict[str, float]:
    if not observations:
        return {key: 0.0 for key in RUBRIC_KEYS}
    return {
        key: sum(_rubric_value(item, key) for item in observations) / len(observations)
        for key in RUBRIC_KEYS
    }


def _weighted(label: str, key: str, weight: int, values: dict[str, float]) -> dict:
    score = round(values[key] / 5 * weight, 1)
    return {"key": key, "label": label, "score": score, "max_score": weight}


def _language_section(values: dict[str, float], age_group: str) -> dict:
    if age_group == "4-7":
        specs = [
            ("因果逻辑", "language_causal_logic", 18),
            ("情节记忆", "language_plot_memory", 12),
            ("词汇丰富度", "language_vocabulary", 22),
            ("细节描写", "language_detail", 20),
            ("角色语言创作", "language_character_voice", 18),
            ("创作主动性", "language_initiative", 10),
        ]
    else:
        specs = [
            ("完整故事闭环", "language_causal_logic", 20),
            ("长线情节记忆", "language_plot_memory", 15),
            ("细节描写", "language_detail", 23),
            ("角色语言创作", "language_character_voice", 20),
            ("词汇丰富度", "language_vocabulary", 14),
            ("创作主动性", "language_initiative", 8),
        ]
    dimensions = [_weighted(*spec, values) for spec in specs]
    return {"base_score": round(sum(item["score"] for item in dimensions), 1), "dimensions": dimensions}


def _independent_section(values: dict[str, float], specs: list[tuple[str, str]]) -> dict:
    dimensions = [_weighted(label, key, 25, values) for label, key in specs]
    return {"score": round(sum(item["score"] for item in dimensions), 1), "dimensions": dimensions}


def _level(score: float, language: bool = False) -> tuple[str, str]:
    if language:
        if score >= 90:
            return "advantage", "语言优势型"
        if score >= 70:
            return "balanced", "能力均衡型"
        return "developing", "潜力待激活"
    if score >= 80:
        return "advantage", "优势突出"
    if score >= 50:
        return "balanced", "发展均衡"
    return "developing", "潜力待激活"


def _growth_index(values: dict[str, float]) -> float:
    # The standard specifically asks progress to be judged from vocabulary,
    # plot memory and detail rather than from empathy or imagination.
    return round(sum(values[key] for key in (
        "language_vocabulary", "language_plot_memory", "language_detail"
    )) / 3 / 5 * 100, 1)


def _progress_bonus(change: float, has_history: bool) -> int:
    if not has_history or change < 1:
        return 0
    if change >= 15:
        return 10
    if change >= 12:
        return 9
    if change >= 9:
        return 8
    if change >= 7:
        return 7
    if change >= 5:
        return 6
    if change >= 3:
        return 5
    return 3


async def _valid_observations(
    db: AsyncSession, story_id: int
) -> tuple[list[Observation], list[StoryMessage]]:
    messages = (await db.execute(
        select(StoryMessage).where(
            StoryMessage.story_id == story_id,
            StoryMessage.role == "child",
        )
    )).scalars().all()
    messages = [item for item in messages if not _is_system_ending_request(item.content)]
    message_ids = {item.id for item in messages}
    observations = (await db.execute(
        select(Observation)
        .where(Observation.story_id == story_id)
        .order_by(Observation.turn_number)
    )).scalars().all()
    return [item for item in observations if item.message_id in message_ids], messages


async def generate_talent_profile(db: AsyncSession, story_id: int) -> TalentProfile | None:
    story = await db.get(Story, story_id)
    if not story:
        return None
    character = await db.get(Character, story.character_id)
    age_group = (character.age_group if character else None) or "8-12"
    observations, child_messages = await _valid_observations(db, story_id)
    values = _averages(observations)

    language = _language_section(values, age_group)
    empathy = _independent_section(values, [
        ("情绪识别与表达", "empathy_emotion"),
        ("换位思考", "empathy_perspective"),
        ("互助与包容情节", "empathy_prosocial"),
        ("温和解决冲突", "empathy_conflict"),
    ])
    imagination = _independent_section(values, [
        ("原创角色或生物", "imagination_character"),
        ("独特虚构场景", "imagination_setting"),
        ("原创世界规则", "imagination_rules"),
        ("支线与隐藏情节", "imagination_side_plot"),
    ])

    history_values: list[dict[str, float]] = []
    if character:
        prior_stories = (await db.execute(
            select(Story)
            .join(Character, Story.character_id == Character.id)
            .where(
                Character.user_id == character.user_id,
                Character.age_group == age_group,
                Story.id != story.id,
                Story.started_at < story.started_at,
                Story.is_deleted.is_(False),
            )
            .order_by(Story.started_at.desc())
            .limit(3)
        )).scalars().all()
        for prior in prior_stories if observations else []:
            prior_observations, _ = await _valid_observations(db, prior.id)
            if prior_observations:
                history_values.append(_averages(prior_observations))

    current_index = _growth_index(values)
    baseline = round(
        sum(_growth_index(item) for item in history_values) / len(history_values), 1
    ) if history_values else None
    change = round(current_index - baseline, 1) if baseline is not None else 0.0
    bonus = _progress_bonus(change, bool(history_values))
    language["progress_bonus"] = bonus
    language["final_score"] = round(language["base_score"] + bonus, 1)
    language["level"], language["level_label"] = _level(language["final_score"], True)
    empathy["level"], empathy["level_label"] = _level(empathy["score"])
    imagination["level"], imagination["level_label"] = _level(imagination["score"])

    growth_memory = {
        "has_history": bool(history_values),
        "compared_story_count": len(history_values),
        "baseline_index": baseline,
        "current_index": current_index,
        "change": change,
        "progress_bonus": bonus,
        "summary": (
            f"与最近 {len(history_values)} 个故事相比，词汇、情节记忆和细节成长指数"
            f"{'提高' if change >= 0 else '下降'} {abs(change):.1f} 分。"
            if history_values else
            (
                "这是首次有效测评，已保存为后续故事的成长基线。"
                if observations else "尚无孩子的有效创作发言，暂不建立成长基线。"
            )
        ),
    }

    message_by_id = {item.id: item for item in child_messages}
    highlights: list[str] = []
    for observation in observations:
        message = message_by_id.get(observation.message_id)
        if not message or not message.content.strip():
            continue
        quote = " ".join(message.content.split())[:120]
        if quote and quote not in highlights:
            highlights.append(quote)

    strengths = []
    suggestions = []
    for section, name in ((language, "语言智能"), (empathy, "共情与人际智能"), (imagination, "想象与空间智能")):
        score = section.get("final_score", section.get("score", 0))
        if score >= (90 if name == "语言智能" else 80):
            strengths.append(f"{name}表现突出，可以继续提供更开放、更复杂的创作任务。")
        elif score < (70 if name == "语言智能" else 50):
            weakest = min(section["dimensions"], key=lambda item: item["score"] / item["max_score"])
            suggestions.append(f"{name}可优先练习“{weakest['label']}”，一次只增加一个小挑战。")
    if not strengths:
        strengths.append("孩子已经留下了可持续追踪的真实创作样本。")
    if not suggestions:
        suggestions.append("保持稳定创作频率，下一份报告会继续与历史基线比较。")

    return TalentProfile(
        story_id=story.id,
        story_title=story.title or story.theme or "未命名故事",
        total_turns=len(observations),
        age_group=age_group,
        completed=story.status == "completed",
        language=language,
        empathy=empathy,
        imagination=imagination,
        growth_memory=growth_memory,
        highlights=highlights[:5],
        total_words=sum(len(item.content) for item in child_messages),
        avg_words_per_turn=round(
            sum(len(item.content) for item in child_messages) / len(child_messages), 1
        ) if child_messages else 0.0,
        strengths=strengths,
        suggestions=suggestions,
    )
