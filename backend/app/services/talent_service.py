"""
Language talent profile generator.

Analyzes observation data collected during story co-creation
and produces a language-intelligence profile based on Gardner's
Multiple Intelligences theory (linguistic dimension).
"""

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observation import Observation
from app.models.story import Story


@dataclass
class LanguageTalentProfile:
    """Complete language talent assessment for one story."""

    story_id: int
    story_title: str
    total_turns: int
    completed: bool

    # Dimension scores (1-5 scale)
    vocabulary_richness: float | None = None       # 词汇丰富度
    descriptive_ability: float | None = None       # 描述能力
    story_structure: float | None = None           # 故事结构/逻辑

    # Trends
    vocabulary_trend: str = ""      # "上升" "稳定" "波动"
    descriptive_trend: str = ""
    structure_trend: str = ""

    # Overall assessment
    overall_level: str = ""         # "语言小天才" / "语言小达人" / "语言小萌芽" / "继续探索中"
    overall_score: float | None = None

    # Creativity
    creativity_flags: list[str] = field(default_factory=list)
    dominant_flag: str = ""

    # Highlights
    vocabulary_highlights: list[str] = field(default_factory=list)
    descriptive_highlights: list[str] = field(default_factory=list)

    # Narrative arc analysis
    total_words_by_child: int = 0
    avg_words_per_turn: float = 0.0

    # Growth suggestions
    strengths: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


LEVEL_DEFINITIONS = {
    "语言小天才": {
        "min_score": 4.0,
        "label": "🌟 语言小天才",
        "description": "你在语言表达方面展现出非凡的天赋！词汇丰富、描述生动、故事逻辑清晰，就像一个天生的小作家。",
    },
    "语言小达人": {
        "min_score": 3.0,
        "label": "✨ 语言小达人",
        "description": "你的语言能力很好！能够用丰富的词汇讲述故事，描述也很生动。继续创作，你会越来越棒！",
    },
    "语言小萌芽": {
        "min_score": 2.0,
        "label": "🌱 语言小萌芽",
        "description": "你的语言能力正在萌芽！虽然有时回答简短，但你已经能参与到故事中了。多读多讲，你的语言天赋会慢慢绽放！",
    },
    "继续探索中": {
        "min_score": 0,
        "label": "🔍 继续探索中",
        "description": "每个孩子都有自己的节奏。现在可能还不太爱表达，但没关系！多听故事、多聊天，语言能力会自然成长。",
    },
}


async def generate_talent_profile(
    db: AsyncSession, story_id: int
) -> LanguageTalentProfile | None:
    """Generate a language talent profile from observation data."""

    story = await db.get(Story, story_id)
    if not story:
        return None

    result = await db.execute(
        select(Observation)
        .where(Observation.story_id == story_id)
        .order_by(Observation.turn_number)
    )
    observations = result.scalars().all()

    profile = LanguageTalentProfile(
        story_id=story_id,
        story_title=story.title or story.theme or "未命名故事",
        total_turns=len(observations),
        completed=(story.status == "completed"),
    )

    if not observations:
        profile.overall_level = "继续探索中"
        profile.suggestions = ["多和故事导演聊天，创作更多故事吧！"]
        return profile

    # ── Score averages ──
    vocab_scores = [o.vocabulary_richness for o in observations if o.vocabulary_richness is not None]
    desc_scores = [o.descriptive_ability for o in observations if o.descriptive_ability is not None]
    struct_scores = [o.story_structure for o in observations if o.story_structure is not None]

    if vocab_scores:
        profile.vocabulary_richness = round(sum(vocab_scores) / len(vocab_scores), 1)
    if desc_scores:
        profile.descriptive_ability = round(sum(desc_scores) / len(desc_scores), 1)
    if struct_scores:
        profile.story_structure = round(sum(struct_scores) / len(struct_scores), 1)

    # ── Trends ──
    profile.vocabulary_trend = _compute_trend(vocab_scores)
    profile.descriptive_trend = _compute_trend(desc_scores)
    profile.structure_trend = _compute_trend(struct_scores)

    # ── Overall score & level ──
    all_scores = [s for s in [profile.vocabulary_richness, profile.descriptive_ability, profile.story_structure] if s is not None]
    if all_scores:
        profile.overall_score = round(sum(all_scores) / len(all_scores), 1)
    else:
        profile.overall_score = 0.0

    for level_name, level_def in LEVEL_DEFINITIONS.items():
        if (profile.overall_score or 0) >= level_def["min_score"]:
            profile.overall_level = level_name
            break

    # ── Creativity flags ──
    flag_counts: dict[str, int] = {}
    for o in observations:
        if o.creativity_flags:
            try:
                flags = json.loads(o.creativity_flags)
                for f in flags:
                    flag_counts[f] = flag_counts.get(f, 0) + 1
            except json.JSONDecodeError:
                pass
    profile.creativity_flags = sorted(flag_counts.keys(), key=lambda f: flag_counts[f], reverse=True)
    if profile.creativity_flags:
        profile.dominant_flag = profile.creativity_flags[0]

    # ── Highlights ──
    for o in observations:
        if o.vocabulary_examples and o.vocabulary_examples.strip():
            profile.vocabulary_highlights.append(o.vocabulary_examples.strip())
        if o.descriptive_examples and o.descriptive_examples.strip():
            profile.descriptive_highlights.append(o.descriptive_examples.strip())

    # ── Word count analysis ──
    # Count words from child messages
    from app.models.message import StoryMessage
    msg_result = await db.execute(
        select(StoryMessage)
        .where(StoryMessage.story_id == story_id, StoryMessage.role == "child")
    )
    child_msgs = msg_result.scalars().all()
    for msg in child_msgs:
        profile.total_words_by_child += len(msg.content)
    if len(child_msgs) > 0:
        profile.avg_words_per_turn = round(profile.total_words_by_child / len(child_msgs), 1)

    # ── Strengths & suggestions ──
    profile.strengths, profile.suggestions = _generate_feedback(profile)

    return profile


def _compute_trend(scores: list[int]) -> str:
    """Compute simple trend: rising, stable, or fluctuating."""
    if len(scores) < 2:
        return "数据不足"
    first_half = sum(scores[: len(scores) // 2]) / (len(scores) // 2)
    second_half = sum(scores[len(scores) // 2 :]) / (len(scores) - len(scores) // 2)
    diff = second_half - first_half
    if diff > 0.5:
        return "上升 📈"
    elif diff < -0.5:
        return "波动 🔄"
    else:
        return "稳定 ➡️"


FLAG_LABELS = {
    "unexpected_twist": "意外转折",
    "rich_imagery": "丰富意象",
    "emotional_depth": "情感深度",
    "logical_consistency": "逻辑一致",
    "humor": "幽默感",
}


def _generate_feedback(profile: LanguageTalentProfile) -> tuple[list[str], list[str]]:
    """Generate strengths and suggestions based on profile data."""
    strengths: list[str] = []
    suggestions: list[str] = []

    if profile.vocabulary_richness is not None:
        if profile.vocabulary_richness >= 4:
            strengths.append("词汇量丰富，善于使用精准生动的词语表达想法")
        elif profile.vocabulary_richness >= 3:
            strengths.append("基本词汇掌握良好，能清晰表达自己的想法")
            suggestions.append("多读故事书，遇到不认识的词可以记下来问问大人")
        else:
            suggestions.append("试着用更多形容词来描述你看到的东西，比如颜色、形状、感觉")

    if profile.descriptive_ability is not None:
        if profile.descriptive_ability >= 4:
            strengths.append("描述能力出色，能用语言在听众脑海中画出画面")
        elif profile.descriptive_ability >= 3:
            strengths.append("具备基本描述能力，能把事情讲清楚")
            suggestions.append("讲故事时可以试着描述'看到了什么、听到了什么、闻到了什么'")
        else:
            suggestions.append("试着描述你最喜欢的一个地方，说说那里是什么样的")

    if profile.story_structure is not None:
        if profile.story_structure >= 4:
            strengths.append("故事逻辑清晰，能把握起因-经过-结果的故事脉络")
        elif profile.story_structure >= 3:
            strengths.append("能够参与故事的情节推进，有一定的逻辑性")
            suggestions.append("讲故事时可以想一想：先发生了什么？然后呢？最后怎么样了？")
        else:
            suggestions.append("讲故事时试试这三个问题：谁？在哪里？做了什么？")

    if profile.creativity_flags:
        flag_names = [FLAG_LABELS.get(f, f) for f in profile.creativity_flags[:3]]
        strengths.append(f"创造力亮点：{'、'.join(flag_names)}")

    if profile.avg_words_per_turn < 5 and profile.total_turns > 1:
        suggestions.append("每次可以多写一点哦！哪怕多写一句话，故事都会变得更精彩")

    if profile.vocabulary_trend == "上升 📈":
        strengths.append("词汇丰富度在持续上升，进步明显！")

    if not strengths:
        strengths.append("已经开始参与故事创作，这是一个很棒的起点！")
    if not suggestions:
        suggestions.append("继续保持创作热情，多写多讲，语言能力会越来越强！")

    return strengths, suggestions
