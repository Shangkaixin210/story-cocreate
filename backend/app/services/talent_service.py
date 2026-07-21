"""
Language talent profile generator v2.

5-dimension model based on Gardner's Multiple Intelligences (linguistic domain):
1. vocabulary_semantic   — 词汇语义敏感度
2. sentence_fluency       — 句式与表达流畅度
3. narrative_completeness — 叙事宏观完整度
4. character_empathy      — 角色语言共情
5. creative_initiative    — 创作主动性

Supports two age groups: 4-7 (lenient) and 8-12 (standard).
"""

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observation import Observation
from app.models.message import StoryMessage
from app.models.story import Story


@dataclass
class LanguageTalentProfile:
    story_id: int
    story_title: str
    total_turns: int
    age_group: str
    completed: bool

    # 5-dimension scores
    avg_vocabulary_semantic: float | None = None
    avg_sentence_fluency: float | None = None
    avg_narrative_completeness: float | None = None
    avg_character_empathy: float | None = None
    avg_creative_initiative: float | None = None
    overall_score: float | None = None

    # Trends
    vocab_trend: str = ""
    fluency_trend: str = ""
    narrative_trend: str = ""
    empathy_trend: str = ""
    initiative_trend: str = ""

    # Levels
    overall_level: str = ""
    level_label: str = ""
    level_description: str = ""
    talent_tags: list[str] = field(default_factory=list)

    # Highlights
    semantic_highlights: list[str] = field(default_factory=list)
    empathy_highlights: list[str] = field(default_factory=list)
    initiative_highlights: list[str] = field(default_factory=list)

    # Stats
    total_words: int = 0
    avg_words_per_turn: float = 0.0

    # Feedback
    strengths: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


# ── Level definitions by age group ──

LEVELS_8_12 = [
    {"name": "语言优势型", "min": 4.0, "label": "🌟 语言优势型",
     "desc": "展现出卓越的语言天赋！能独立搭建完整故事闭环，运用丰富的修辞手法，为角色赋予差异化台词与内心独白。你的文字里住着一位天生的创作者。建议：多读经典文学作品，参加写作或演讲活动，让天赋在系统的训练中进一步绽放。"},
    {"name": "能力均衡型", "min": 2.5, "label": "✨ 能力均衡型",
     "desc": "语言能力发展均衡！能完成基础故事框架，有一定修饰和情节意识。每一段创作都在为语言能力添砖加瓦。建议：多尝试不同类型的写作（记叙文、诗歌、剧本），在多样化练习中找到自己最擅长的表达方式。"},
    {"name": "潜力待激活", "min": 0, "label": "🌱 潜力待激活",
     "desc": "语言天赋的种子正在蓄力。可能目前回答较为简短或被框架限制，但每一次开口都在积累语言素材。建议：从感兴趣的话题切入，用聊天的形式多讲故事，降低写作压力，让语言自然流动起来。"},
]

LEVELS_4_7 = [
    {"name": "语言优势型", "min": 3.5, "label": "🧚 语言优势型",
     "desc": "语言表达非常活跃！喜欢创编故事、主动描述画面、模仿角色说话，口语输出欲旺盛。这是语言天赋的早期闪光信号。建议：多读绘本，鼓励TA把看到的画面用自己的话说出来，表扬每一次主动表达。"},
    {"name": "能力均衡型", "min": 2.5, "label": "🎈 能力均衡型",
     "desc": "语言能力发展均衡！能跟随引导参与故事，有基本的表达和描述意识。这是健康发展的节奏。建议：多用开放式问题激发表达，减少选择式提问，给TA更多自由发挥空间。"},
    {"name": "潜力待激活", "min": 0, "label": "🌿 潜力待激活",
     "desc": "语言表达的种子刚刚萌芽。可能更倾向于听故事而非讲故事，或者需要更多时间和安全感来开口。这完全正常——每个孩子都有自己的节奏。建议：从模仿角色声音开始，用游戏的方式降低表达门槛，多听多输入。"},
]


def _compute_trend(scores: list[int]) -> str:
    if len(scores) < 2: return "数据不足"
    mid = len(scores) // 2
    first = sum(scores[:mid]) / mid
    second = sum(scores[mid:]) / (len(scores) - mid)
    diff = second - first
    if diff > 0.5: return "上升 📈"
    elif diff < -0.5: return "回落 🔄"
    else: return "稳定 ➡️"


def _is_system_ending_request(text: str) -> bool:
    normalized = "".join(text.split())
    return "请从刚才的情节继续" in normalized and "完整的大结局" in normalized


async def generate_talent_profile(db: AsyncSession, story_id: int) -> LanguageTalentProfile | None:
    story = await db.get(Story, story_id)
    if not story:
        return None

    result = await db.execute(
        select(Observation)
        .where(Observation.story_id == story_id)
        .order_by(Observation.turn_number)
    )
    obs_list = result.scalars().all()

    # Observations must be backed by genuine child messages. Older versions
    # accidentally saved the UI's "write the ending" command as child input.
    msg_result = await db.execute(
        select(StoryMessage)
        .where(StoryMessage.story_id == story_id, StoryMessage.role == "child")
    )
    all_child_msgs = msg_result.scalars().all()
    child_msgs = [m for m in all_child_msgs if not _is_system_ending_request(m.content)]
    child_by_id = {message.id: message for message in child_msgs}
    obs_list = [observation for observation in obs_list if observation.message_id in child_by_id]

    # Get age_group from character
    from app.models.character import Character
    char = await db.get(Character, story.character_id)
    age_group = char.age_group or "8-12" if char else "8-12"

    p = LanguageTalentProfile(
        story_id=story_id,
        story_title=story.title or story.theme or "未命名故事",
        total_turns=len(obs_list),
        age_group=age_group,
        completed=(story.status == "completed"),
    )

    if not obs_list:
        p.overall_level = "继续探索中"
        p.suggestions = ["多和故事导演聊天，创作更多故事吧！"]
        return p

    # ── Averages ──
    scores = {
        "vocab": [o.vocabulary_semantic for o in obs_list if o.vocabulary_semantic is not None],
        "fluency": [o.sentence_fluency for o in obs_list if o.sentence_fluency is not None],
        "narrative": [o.narrative_completeness for o in obs_list if o.narrative_completeness is not None],
        "empathy": [o.character_empathy for o in obs_list if o.character_empathy is not None],
        "initiative": [o.creative_initiative for o in obs_list if o.creative_initiative is not None],
    }

    p.avg_vocabulary_semantic = round(sum(scores["vocab"]) / len(scores["vocab"]), 1) if scores["vocab"] else None
    p.avg_sentence_fluency = round(sum(scores["fluency"]) / len(scores["fluency"]), 1) if scores["fluency"] else None
    p.avg_narrative_completeness = round(sum(scores["narrative"]) / len(scores["narrative"]), 1) if scores["narrative"] else None
    p.avg_character_empathy = round(sum(scores["empathy"]) / len(scores["empathy"]), 1) if scores["empathy"] else None
    p.avg_creative_initiative = round(sum(scores["initiative"]) / len(scores["initiative"]), 1) if scores["initiative"] else None

    # ── Trends ──
    p.vocab_trend = _compute_trend(scores["vocab"])
    p.fluency_trend = _compute_trend(scores["fluency"])
    p.narrative_trend = _compute_trend(scores["narrative"])
    p.empathy_trend = _compute_trend(scores["empathy"])
    p.initiative_trend = _compute_trend(scores["initiative"])

    # ── Overall score ──
    all_avgs = [v for v in [p.avg_vocabulary_semantic, p.avg_sentence_fluency,
                             p.avg_narrative_completeness, p.avg_character_empathy,
                             p.avg_creative_initiative] if v is not None]
    p.overall_score = round(sum(all_avgs) / len(all_avgs), 1) if all_avgs else 0.0

    # ── Level ──
    levels = LEVELS_4_7 if age_group == "4-7" else LEVELS_8_12
    for lv in levels:
        if (p.overall_score or 0) >= lv["min"]:
            p.overall_level = lv["name"]
            p.level_label = lv["label"]
            p.level_description = lv["desc"]
            break

    # ── Talent tags ──
    tags = []
    if (p.avg_vocabulary_semantic or 0) >= 4: tags.append("词汇小达人")
    if (p.avg_sentence_fluency or 0) >= 4: tags.append("流畅叙事者")
    if (p.avg_narrative_completeness or 0) >= 4: tags.append("故事架构师")
    if (p.avg_character_empathy or 0) >= 4: tags.append("角色灵魂师")
    if (p.avg_creative_initiative or 0) >= 4: tags.append("创意探险家")
    if not tags: tags.append("语言探索者")
    p.talent_tags = tags

    # Highlights must quote the child and must never display evaluator-generated
    # prose or the story director's writing.
    def child_quote(observation: Observation) -> str:
        message = child_by_id.get(observation.message_id)
        if not message or not message.content.strip():
            return ""
        text = " ".join(message.content.split())
        return f"“{text[:100]}{'…' if len(text) > 100 else ''}”"

    # ── Highlights ──
    for o in obs_list:
        quote = child_quote(o)
        if not quote:
            continue
        if (o.vocabulary_semantic or 0) >= 3 and quote not in p.semantic_highlights:
            p.semantic_highlights.append(quote)
        if (o.character_empathy or 0) >= 3 and quote not in p.empathy_highlights:
            p.empathy_highlights.append(quote)
        if (o.creative_initiative or 0) >= 3 and quote not in p.initiative_highlights:
            p.initiative_highlights.append(quote)

    # ── Word count ──
    p.total_words = sum(len(m.content) for m in child_msgs)
    p.avg_words_per_turn = round(p.total_words / len(child_msgs), 1) if child_msgs else 0.0

    # ── Strengths & suggestions ──
    p.strengths, p.suggestions = _generate_feedback(p)

    return p


def _generate_feedback(p: LanguageTalentProfile) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    suggestions: list[str] = []

    dims = [
        (p.avg_vocabulary_semantic, "词汇语义敏感度",
         "善于使用丰富的修饰词、情绪词和修辞手法，语言富有感染力",
         "试试在描述中加入比喻——'像……一样'的句式能让画面立刻生动起来"),
        (p.avg_sentence_fluency, "句式表达流畅度",
         "叙事清晰连贯，表达流畅自然",
         "讲故事时可以试着先说'首先……然后……最后……'，这样听众能更好地跟上你的节奏"),
        (p.avg_narrative_completeness, "叙事完整度",
         "能构建完整的起因-冲突-解决的故事结构，很有导演思维",
         "想一想你的故事里有没有一个'问题'要解决？有了问题和解决办法，故事会更精彩"),
        (p.avg_character_empathy, "角色共情能力",
         "擅长让角色说话、思考和感受，故事里的人物活起来了",
         "试试给你的角色写一句TA最想说的话，或者TA此刻心里在想什么"),
        (p.avg_creative_initiative, "创作主动性",
         "创作欲满满！不满足于框架，主动拓展新剧情和新细节",
         "每次多一点：在AI给出的情节之外，再加一个你自己想到的小插曲"),
    ]

    for score, name, strength_msg, suggestion_msg in dims:
        if score is not None:
            if score >= 4:
                strengths.append(f"{name}：{strength_msg}")
            elif score < 2.5 and not (p.age_group == "4-7" and score >= 2):
                suggestions.append(suggestion_msg)

    if p.vocab_trend == "上升 📈":
        strengths.append("词汇语义敏感度持续上升，进步明显！")
    if p.initiative_trend == "上升 📈":
        strengths.append("创作主动性越来越强，故事越写越精彩！")

    if p.avg_words_per_turn < 5 and p.total_turns > 1:
        suggestions.append("每次多写一点点，哪怕多一句话，故事都会变得更精彩")

    if not strengths:
        strengths.append("已经开始用语言创作故事，这是一个了不起的起点！")
    if not suggestions:
        suggestions.append("继续保持创作热情，你的语言天赋正在闪闪发光！")

    return strengths[:5], suggestions[:5]
