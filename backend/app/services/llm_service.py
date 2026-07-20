import asyncio
import json
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.config import settings
from app.prompts.story_director import build_system_prompt


HEARTBEAT_INTERVAL = 8  # seconds — keep proxies/load-balancers alive


def compute_observation(child_text: str, age_group: str = "") -> dict:
    """Programmatic fallback: analyze child's text for 5 language intelligence dimensions.

    Based on Gardner's Multiple Intelligences (linguistic domain).
    """
    if not child_text or not child_text.strip():
        return {
            "vocabulary_semantic": 1, "vocabulary_semantic_examples": "",
            "sentence_fluency": 1, "sentence_fluency_examples": "",
            "narrative_completeness": 1, "narrative_structure_note": "无输入",
            "character_empathy": 1, "character_empathy_examples": "",
            "creative_initiative": 1, "creative_initiative_examples": "",
            "creativity_flags": [],
        }

    text = child_text.strip()
    words = [w for w in text if w not in '，。！？、；：""''（）']
    word_count = len(text.replace(' ', ''))
    sentences = [s.strip() for s in text.replace("！", "。").replace("？", "。").replace("!", ".").replace("?", ".").split("。") if len(s.strip()) >= 2]

    # ── 1. vocabulary_semantic ──
    modifier_keywords = ["很", "非常", "特别", "极了", "极了", "最", "更", "太",
                        "慢慢", "轻轻", "悄悄", "渐渐", "忽然", "突然", "已经", "正在"]
    emotion_keywords = ["开心", "难过", "害怕", "生气", "惊讶", "兴奋", "担心", "喜欢",
                       "感动", "伤心", "紧张", "骄傲", "害羞", "好奇", "着急", "幸福"]
    concrete_keywords = []  # detected by word length
    metaphor_signals = ["像", "仿佛", "好像", "如同", "似乎", "变成", "成了", "一样"]
    personification_signals = ["说", "笑", "哭", "想", "知道", "告诉", "问", "回答"]

    mod_count = sum(1 for kw in modifier_keywords if kw in text)
    emo_count = sum(1 for kw in emotion_keywords if kw in text)
    long_words = [w for w in text if len(w.encode('utf-8', errors='ignore')) >= 6]  # longer Chinese words
    meta_count = sum(1 for kw in metaphor_signals if kw in text)
    pers_count = sum(1 for kw in personification_signals if kw in text and any(c in text for c in ["：", "「", "\"", "“"]))

    semantic_score = 1
    if mod_count >= 3 and meta_count >= 1: semantic_score = 5
    elif mod_count >= 2 or (meta_count >= 1 and emo_count >= 1): semantic_score = 4
    elif mod_count >= 1 or emo_count >= 1: semantic_score = 3
    elif word_count >= 10: semantic_score = 2

    semantic_examples = []
    if mod_count > 0: semantic_examples.append(f"修饰词×{mod_count}")
    if emo_count > 0: semantic_examples.append(f"情绪词×{emo_count}")
    if meta_count > 0: semantic_examples.append(f"比喻/拟人×{meta_count}")
    semantic_examples_str = "; ".join(semantic_examples) if semantic_examples else ""

    # ── 2. sentence_fluency ──
    fluency = 1
    if len(sentences) >= 4 and all(len(s) >= 5 for s in sentences):
        fluency = 5
    elif len(sentences) >= 3:
        fluency = 4
    elif len(sentences) >= 2:
        fluency = 3
    elif len(sentences) >= 1 and len(sentences[0]) >= 10:
        fluency = 2

    fluency_examples = sentences[0][:80] if sentences else ""

    # ── 3. narrative_completeness ──
    cause_signals = ["因为", "所以", "由于", "于是", "因此"]
    conflict_signals = ["但是", "可是", "突然", "忽然", "没想到", "竟然", "居然", "不过"]
    resolve_signals = ["然后", "后来", "最后", "终于", "结果", "发现", "解决了", "成功了"]
    ending_signals = ["结束", "回家", "离开", "回到", "从此", "以后", "好了", "完了", "故事"]

    cause_count = sum(1 for kw in cause_signals if kw in text)
    conflict_count = sum(1 for kw in conflict_signals if kw in text)
    resolve_count = sum(1 for kw in resolve_signals if kw in text)
    ending_count = sum(1 for kw in ending_signals if kw in text)

    struct_signals = cause_count + conflict_count + resolve_count + ending_count
    completeness = 1
    if cause_count >= 1 and conflict_count >= 1 and resolve_count >= 1: completeness = 5
    elif conflict_count >= 1 and resolve_count >= 1: completeness = 4
    elif cause_count >= 1 or conflict_count >= 1: completeness = 3
    elif len(sentences) >= 2: completeness = 2

    # ── 4. character_empathy ──
    dialogue_signals = ["说", "问", "回答", "喊道", "叫道", "说道", "告诉", "喊", "叫",
                       "：", "「", "」", "\"", "\"", "“", "”"]
    thought_signals = ["想", "觉得", "感到", "认为", "希望", "害怕", "担心", "开心"]
    emotion_in_context = any(kw in text for kw in ["开心", "难过", "害怕", "生气", "哭了", "笑了", "跳起来", "发抖"])

    dialogue_count = sum(1 for kw in dialogue_signals if kw in text)
    thought_count = sum(1 for kw in thought_signals if kw in text)

    empathy = 1
    if dialogue_count >= 3 and thought_count >= 1: empathy = 5
    elif dialogue_count >= 2: empathy = 4
    elif dialogue_count >= 1 or thought_count >= 1: empathy = 3
    elif emotion_in_context: empathy = 2

    empathy_examples = ""
    if dialogue_count >= 1: empathy_examples += f"角色对话×{dialogue_count} "
    if thought_count >= 1: empathy_examples += f"心理活动×{thought_count}"
    empathy_examples = empathy_examples.strip()

    # ── 5. creative_initiative ──
    # Detect if child goes beyond the expected response: new characters, locations, objects
    new_element_signals = 0
    for kw in ["新", "突然出现", "没想到", "其实", "另外", "还有", "之前", "原来", "秘密", "隐藏"]:
        if kw in text: new_element_signals += 1

    # Count unique proper nouns / named entities (rough heuristic: consecutive capital/long words)
    named_count = len([w for w in text if len(w.encode('utf-8', errors='ignore')) >= 9])

    initiative = 1
    if new_element_signals >= 3 and word_count >= 50: initiative = 5
    elif new_element_signals >= 2: initiative = 4
    elif new_element_signals >= 1: initiative = 3
    elif word_count >= 20: initiative = 2

    initiative_examples = f"新增元素×{new_element_signals}" if new_element_signals > 0 else ""

    # ── Adjust for age group ──
    if age_group == "4-7":
        # Younger children: lenient scoring, reward any expression
        semantic_score = min(5, semantic_score + 1)
        fluency = min(5, fluency + 1)
        completeness = min(5, completeness + (0 if word_count < 5 else 1))
        empathy = min(5, empathy + (1 if word_count > 10 else 0))
        initiative = min(5, initiative + 1)

    # ── Creativity flags ──
    flags = []
    for kw, flag in [("突然", "unexpected_twist"), ("像", "metaphor_usage"), ("仿佛", "metaphor_usage"),
                     ("说", "original_dialogue"), ("生气", "emotional_depth"), ("开心", "emotional_depth"),
                     ("哭了", "emotional_depth"), ("笑了", "emotional_depth"),
                     ("好像", "personification"), ("因为", "logical_consistency"), ("所以", "logical_consistency")]:
        if kw in text and flag not in flags:
            flags.append(flag)

    return {
        "vocabulary_semantic": semantic_score,
        "vocabulary_semantic_examples": semantic_examples_str,
        "sentence_fluency": fluency,
        "sentence_fluency_examples": fluency_examples,
        "narrative_completeness": completeness,
        "narrative_structure_note": f"起因×{cause_count} 冲突×{conflict_count} 解决×{resolve_count} 结尾×{ending_count}",
        "character_empathy": empathy,
        "character_empathy_examples": empathy_examples,
        "creative_initiative": initiative,
        "creative_initiative_examples": initiative_examples,
        "creativity_flags": flags,
    }


def _try_parse_json_line(line: str) -> dict | None:
    """Try to parse a line as JSON. Returns parsed dict or None.

    Handles common DeepSeek output errors:
    - Unescaped Chinese quotes inside JSON strings (e.g. "text":"他说"你好"")
    - Extra commas or trailing content
    """
    if not line or not line.startswith("{"):
        return None

    # Attempt 1: direct parse
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        pass

    # Attempt 2: replace Chinese double quotes inside JSON string values
    # Pattern: inside "text":"...", replace "" with 「」
    try:
        fixed = _fix_json_quotes(line)
        if fixed != line:
            return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Attempt 3: try to extract a JSON object with regex
    import re
    match = re.search(r'\{.+"type":\s*"(narrative|question|observation|done)".+?\}\s*$', line)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _fix_json_quotes(text: str) -> str:
    """Replace Chinese double quotes inside JSON string values with corner brackets."""
    import re
    # Find text between "text":" and the closing " before the next JSON key or end
    # This is a simplified heuristic: replace “ and ” inside text values
    result = []
    in_text_value = False
    i = 0
    while i < len(text):
        if not in_text_value and text[i:i+7] == '"text":"':
            result.append(text[i:i+7])
            i += 7
            in_text_value = True
            continue
        if in_text_value:
            if text[i] == '"' and i + 1 < len(text) and text[i+1] == '"':
                result.append('“')  # "
                i += 1
            elif text[i] == '"' and i + 1 < len(text) and text[i+1] == '"':
                result.append('”')  # "
                i += 1
            elif text[i] == '"' and (i + 1 >= len(text) or text[i+1] in ',}'):
                # End of text value
                result.append('"')
                in_text_value = False
            elif text[i] == '"':
                # Unescaped quote inside text — replace with 「
                # Look ahead to find the matching unescaped quote
                result.append('「')  # 「
            else:
                result.append(text[i])
        else:
            result.append(text[i])
        i += 1
    return ''.join(result)


async def _emit_plain_text(plain_text: str, queue: asyncio.Queue):
    """Parse plain-text LLM output into narrative + question events.

    DeepSeek sometimes ignores the JSON Lines format and outputs plain text directly.
    This fallback salvages the content: the story text becomes narrative chunks,
    and the last sentence (if it ends with ? or ？) becomes the question.

    Also strips out any raw JSON-looking lines that leaked through.
    """
    import re

    text = plain_text.strip()
    if not text:
        return

    # ── Strip raw JSON objects/lines that leaked through ──
    # Remove lines that look like {"type":"...",...}
    text = re.sub(r'\{"type"\s*:\s*"(?:narrative|question|observation|done|ending)"[^}]*\}', '', text)
    # Remove standalone JSON fragments
    text = re.sub(r'"type"\s*:\s*"(?:narrative_chunk|question|observation|done)"', '', text)
    text = text.strip()
    if not text:
        return

    # Try to split into narrative + question
    question_markers = ["？", "?", "吗", "呢", "什么", "怎么", "哪里", "哪个"]
    sentences = text.replace("！", "。").replace("?", "？").split("。")

    narrative_parts = []
    question = ""

    found_question = False
    for i, sent in enumerate(sentences):
        sent = sent.strip()
        if not sent:
            continue
        # Check if this sentence looks like a question (last non-empty or contains markers)
        is_last = (i == len(sentences) - 1)
        has_marker = any(m in sent for m in question_markers)
        if (is_last and has_marker) or (has_marker and not found_question and is_last):
            question = sent + ("？" if not sent.endswith(("？", "?")) else "")
            found_question = True
        else:
            narrative_parts.append(sent)

    # Rebuild narrative
    narrative = "。".join(narrative_parts)
    if narrative and not narrative.endswith(("。", "！", "!", ".", "~")):
        narrative += "。"

    # If no question found, craft a generic one
    if not question:
        question = "你觉得接下来会发生什么呢？"

    # Emit narrative in chunks of ~30 chars for streaming effect
    chunk_size = 30
    for i in range(0, len(narrative), chunk_size):
        await queue.put({"type": "narrative_chunk", "text": narrative[i:i + chunk_size]})

    if question:
        await queue.put({"type": "question", "text": question})


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=60.0,
        )
        self.model = settings.llm_model

    async def generate_turn(
        self,
        messages: list[dict],
        character_name: str = "",
        character_type: str = "",
        personality: str = "",
        theme: str = "",
        is_first_turn: bool = False,
        age_group: str = "8-12",
    ) -> AsyncGenerator[dict, None]:
        """
        Stream-generate a story turn from the LLM.

        Uses an asyncio.Queue so heartbeat events fire independently
        of LLM chunk arrival.  This prevents proxy/browser timeouts.
        """
        system_prompt = build_system_prompt(
            character_name=character_name,
            character_type=character_type,
            personality=personality,
            theme=theme,
            is_first_turn=is_first_turn,
            age_group=age_group,
        )

        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                stream=True,
                temperature=0.8,
                max_tokens=1024,
                timeout=60.0,
            )
        except Exception as e:
            raise LLMServiceError(f"AI 导演暂时无法响应: {str(e)[:100]}")

        # ── Queue-based stream + independent heartbeat ──
        queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=32)
        stream_done = asyncio.Event()

        async def pump_chunks():
            """Read LLM chunks → parse JSON Lines (with plain-text prefix handling) → enqueue."""
            import re

            buffer = ""
            pending_plain = ""      # Text accumulated BEFORE first valid JSON line
            seen_valid_json = False  # Whether we've successfully parsed at least one JSON line

            try:
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content or ""
                    buffer += delta

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        # ── Try to parse as JSON (with basic error recovery) ──
                        parsed = _try_parse_json_line(line)
                        if parsed is not None:
                            # Valid JSON found! Flush any pending plain text as narrative
                            seen_valid_json = True
                            if pending_plain.strip():
                                await _emit_plain_text(pending_plain.strip(), queue)
                                pending_plain = ""

                            t = parsed.get("type")
                            if t == "narrative":
                                chunk = {"type": "narrative_chunk", "text": parsed.get("text", "")}
                                if parsed.get("image_prompt"):
                                    chunk["image_prompt"] = parsed["image_prompt"]
                                await queue.put(chunk)
                            elif t == "ending":
                                await queue.put({"type": "ending", "text": parsed.get("text", "")})
                            elif t == "question":
                                await queue.put({"type": "question", "text": parsed.get("text", "")})
                            elif t == "observation":
                                await queue.put({"type": "observation", "data": parsed.get("data", {})})
                            elif t == "done":
                                await queue.put({"type": "done"})
                                stream_done.set()
                                return
                        else:
                            # Not valid JSON
                            if not seen_valid_json:
                                # Haven't seen JSON yet — accumulate as potential prefix
                                pending_plain += line
                            # else: seen JSON before, skip noise between JSON lines

                # ── Stream ended ──
                if buffer.strip():
                    parsed = _try_parse_json_line(buffer.strip())
                    if parsed is not None and parsed.get("type") == "done":
                        await queue.put({"type": "done"})
                        stream_done.set()
                        return
                    if not seen_valid_json:
                        pending_plain += buffer

                # If we never saw valid JSON, treat everything as plain text
                if not seen_valid_json and pending_plain.strip():
                    await _emit_plain_text(pending_plain.strip(), queue)

            except Exception as e:
                import traceback
                traceback.print_exc()
                if pending_plain.strip():
                    await _emit_plain_text(pending_plain.strip(), queue)
            finally:
                await queue.put({"type": "done"})
                stream_done.set()

        async def pump_heartbeats():
            """Send heartbeat events on a fixed cadence."""
            while not stream_done.is_set():
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not stream_done.is_set():
                    await queue.put({"type": "heartbeat"})

        # Launch both pumps concurrently
        chunk_task = asyncio.create_task(pump_chunks())
        heartbeat_task = asyncio.create_task(pump_heartbeats())

        # Read from queue and yield until done
        done_received = False
        while not done_received:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL + 2)
            except asyncio.TimeoutError:
                # Queue was silent for too long — inject heartbeat manually
                yield {"type": "heartbeat"}
                continue

            if event is None:
                continue

            if event["type"] == "done":
                done_received = True

            yield event

        # Cleanup
        stream_done.set()
        chunk_task.cancel()
        heartbeat_task.cancel()
        try:
            await asyncio.gather(chunk_task, heartbeat_task, return_exceptions=True)
        except asyncio.CancelledError:
            pass


    async def evaluate_turn(self, child_text: str, age_group: str = "8-12") -> dict:
        """Call Talent Evaluator agent to analyze child's language output.

        Returns a dict with the 5-dimension observation data.
        Falls back to compute_observation() on any error.
        """
        from app.prompts.talent_evaluator import build_evaluator_prompt

        if not child_text or not child_text.strip():
            return compute_observation(child_text, age_group)

        evaluator_prompt = build_evaluator_prompt(age_group)

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": evaluator_prompt},
                    {"role": "user", "content": child_text.strip()},
                ],
                stream=False,
                temperature=0.3,   # Low temp for consistent scoring
                max_tokens=500,
                timeout=15.0,
            )
            content = (resp.choices[0].message.content or "").strip()
            # Some compatible model providers wrap JSON in Markdown fences.
            if content.startswith("```"):
                content = content.removeprefix("```json").removeprefix("```")
                content = content.removesuffix("```").strip()
            data = json.loads(content)
            score = lambda key: max(1, min(5, int(data.get(key, 1))))
            # Ensure all required fields exist
            return {
                "vocabulary_semantic": score("vocabulary_semantic"),
                "vocabulary_semantic_examples": data.get("vocabulary_semantic_examples", ""),
                "sentence_fluency": score("sentence_fluency"),
                "sentence_fluency_examples": data.get("sentence_fluency_examples", ""),
                "narrative_completeness": score("narrative_completeness"),
                "narrative_structure_note": data.get("narrative_structure_note", ""),
                "character_empathy": score("character_empathy"),
                "character_empathy_examples": data.get("character_empathy_examples", ""),
                "creative_initiative": score("creative_initiative"),
                "creative_initiative_examples": data.get("creative_initiative_examples", ""),
                "creativity_flags": data.get("creativity_flags", []),
            }
        except Exception:
            # Fallback to programmatic scoring
            return compute_observation(child_text, age_group)


class LLMServiceError(Exception):
    pass


# Singleton
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
