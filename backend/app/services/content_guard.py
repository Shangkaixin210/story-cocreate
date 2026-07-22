"""
Content safety guard for the story co-creation module.

Scans child input for violent, aggressive, or inappropriate language
and returns a friendly, age-appropriate notice.

All detection is keyword/rule-based (no LLM dependency) for instant response.
"""

from dataclasses import dataclass

# ── Keyword dictionaries ──

# Heavy violence — needs strong redirection
HEAVY_KEYWORDS = {
    "杀死", "杀掉", "打死", "砍死", "炸死", "捅死", "枪毙",
    "自杀", "去死", "死掉", "掐死", "毒死", "烧死",
    "谋杀", "行凶", "凶手", "屠杀", "灭口",
}

# Moderate violence — needs gentle reminder
MODERATE_KEYWORDS = {
    "杀", "死", "砍", "炸", "枪", "血", "刀", "剑",
    "鞭", "抽", "砸", "摔", "踹", "踢飞",
    "恐怖", "可怕", "魔鬼", "恶魔", "地狱",
}

# Mild — may be okay in context but worth noting
MILD_KEYWORDS = {
    "打", "骂", "揍", "踢", "推", "抢", "偷", "骗",
    "恨", "讨厌", "滚", "笨", "蠢", "傻",
}

# Phrases that are clearly NOT violent (to avoid false positives)
SAFE_PHRASES = {
    "打败怪兽", "打怪兽", "打坏人", "打败坏人",
    "打篮球", "打游戏", "打牌", "打水漂", "打雪仗",
    "打开", "打扫", "打电话", "打招呼", "打喷嚏",
    "打扰", "打算", "打印", "打折", "打针",
    "死党", "笑死", "乐死", "开心死", "高兴死",
    "热血", "血压", "血管", "鲜血", "血型",
    "骂人是不对的", "不能骂人",
}


# ── Engagement signals for child interaction exceptions ──

STUCK_KEYWORDS = {"不知道", "不会", "不知道写什么", "想不到", "没想好", "随便", "都行", "嗯", "哦", "好", "行", "可以", "还行"}
OFF_TOPIC_KEYWORDS = {"游戏", "手机", "零食", "作业", "考试", "分数", "老师批评", "同学欺负", "动画片", "玩具", "奥特曼", "王者荣耀", "吃鸡"}
WANT_TO_STOP_KEYWORDS = {"不想写了", "不想玩了", "好累", "累了", "没意思", "不好玩", "写不动", "不玩了", "结束吧", "算了吧", "不要了"}

@dataclass
class EngagementResult:
    issue_type: str   # "stuck" | "off_topic" | "want_to_stop" | "OK"
    prompt_hint: str  # Extra instruction to inject into the system prompt


def check_engagement(text: str) -> EngagementResult:
    """Detect if the child is stuck, off-topic, or wants to stop.

    Returns EngagementResult with hints for the story director.
    """
    if not text or not text.strip():
        return EngagementResult(issue_type="OK", prompt_hint="")

    normalized = text.strip()

    # 1. Want to stop?
    for kw in WANT_TO_STOP_KEYWORDS:
        if kw in normalized:
            return EngagementResult(
                issue_type="want_to_stop",
                prompt_hint="孩子表达了不想继续的情绪。请用温暖的方式回应：先共情,然后给故事一个简短而温暖的结局,使用ending事件收尾。不要追问。",
            )

    # 2. Stuck / can't think?
    word_count = len(normalized.replace(" ", ""))
    if word_count <= 3:
        return EngagementResult(
            issue_type="stuck",
            prompt_hint='孩子似乎卡住了，回答很短。请给出1-2个具体的续写方向供TA选择，鼓励TA大胆想。不要只说再想想。',
        )
    for kw in STUCK_KEYWORDS:
        if kw == normalized or (kw in normalized and word_count <= 5):
            return EngagementResult(
                issue_type="stuck",
                prompt_hint="孩子的回答很短或表示不知道。请给出2个具体有趣的续写建议让TA选，降低创作压力。先肯定TA之前的贡献再引导。",
            )

    # 3. Off-topic?
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in normalized:
            return EngagementResult(
                issue_type="off_topic",
                prompt_hint='孩子聊到了和故事无关的话题。请用轻松幽默的方式把注意力拉回故事，在下一段叙事中自然地衔接回故事主线。',
            )

    return EngagementResult(issue_type="OK", prompt_hint="")


@dataclass
class SafetyResult:
    is_flagged: bool
    level: str          # "heavy" | "moderate" | "mild" | "safe"
    triggered_word: str
    kind_message: str   # Child-friendly reminder text


def check_content(text: str) -> SafetyResult:
    """Scan child input for violent/inappropriate content.

    Returns SafetyResult with a child-friendly message if flagged.
    """
    if not text or not text.strip():
        return SafetyResult(
            is_flagged=False, level="safe", triggered_word="",
            kind_message="",
        )

    # Normalize
    normalized = text.strip()

    # Check safe phrases first (avoid false positives)
    for safe in SAFE_PHRASES:
        if safe in normalized:
            # Remove the safe part before checking
            normalized = normalized.replace(safe, " ")

    # ── Heavy check ──
    for word in HEAVY_KEYWORDS:
        if word in normalized:
            return SafetyResult(
                is_flagged=True,
                level="heavy",
                triggered_word=word,
                kind_message=(
                    "🤗 故事导演注意到你用到了一些不太友好的词语。"
                    "在我们的故事里，我们可以用更温暖的方式解决问题哦！"
                    "比如：用智慧说服、用友谊感化、用团队合作——这些比暴力更有力量呢！"
                ),
            )

    # ── Moderate check ──
    for word in MODERATE_KEYWORDS:
        if word in normalized:
            return SafetyResult(
                is_flagged=True,
                level="moderate",
                triggered_word=word,
                kind_message=(
                    "💛 故事导演想提醒你：在故事中，角色之间的冲突可以有很多积极的解决方式。"
                    "试着想一想：除了对抗，还能用什么方法来化解矛盾呢？"
                ),
            )

    # ── Mild check ──
    for word in MILD_KEYWORDS:
        if word in normalized:
            return SafetyResult(
                is_flagged=True,
                level="mild",
                triggered_word=word,
                kind_message=(
                    "📖 每一个精彩的故事都充满了友善和智慧。"
                    "让我们用更积极的语言来讲述故事吧！"
                ),
            )

    return SafetyResult(
        is_flagged=False, level="safe", triggered_word="", kind_message="",
    )
