import asyncio
import json
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.config import settings
from app.prompts.story_director import build_system_prompt


HEARTBEAT_INTERVAL = 8  # seconds — keep proxies/load-balancers alive


def compute_observation(child_text: str) -> dict:
    """Programmatic fallback: analyze child's text when LLM doesn't provide observation data.

    Uses objective metrics that don't depend on LLM following format instructions.
    """
    if not child_text or not child_text.strip():
        return {"vocabulary_richness": 1, "vocabulary_examples": "",
                "descriptive_ability": 1, "descriptive_examples": "",
                "story_structure": 1, "structure_note": "无输入", "creativity_flags": []}

    text = child_text.strip()
    words = text.split()
    char_count = len(text)

    # ── Vocabulary richness (1-5) ──
    unique_words = len(set(w.lower() for w in words)) if words else 0
    word_count = len(words)
    unique_ratio = unique_words / max(word_count, 1)
    # Score based on word count and unique ratio
    if word_count >= 50 and unique_ratio >= 0.7:
        vocab = 5
    elif word_count >= 30 and unique_ratio >= 0.5:
        vocab = 4
    elif word_count >= 15:
        vocab = 3
    elif word_count >= 5:
        vocab = 2
    else:
        vocab = 1

    # Extract potential highlight words (longer, more specific words)
    highlight_words = [w for w in words if len(w) >= 4 and w.lower() not in
                       {'this', 'that', 'the', 'and', 'for', 'with', 'from', 'have', 'what', 'when'}]
    vocab_examples = ", ".join(highlight_words[:8]) if highlight_words else ""

    # ── Descriptive ability (1-5) ──
    # Heuristic: longer sentences and use of adjectives/adverbs suggest better description
    sentences = [s.strip() for s in text.replace("！", "。").replace("？", "。").replace("!", ".").replace("?", ".").split("。") if s.strip()]
    avg_sentence_len = char_count / max(len(sentences), 1)
    if avg_sentence_len >= 30 and len(sentences) >= 2:
        desc = 5
    elif avg_sentence_len >= 20 and len(sentences) >= 1:
        desc = 4
    elif avg_sentence_len >= 10:
        desc = 3
    elif char_count >= 10:
        desc = 2
    else:
        desc = 1

    desc_examples = sentences[0][:100] if sentences else ""

    # ── Story structure (1-5) ──
    # Heuristic: presence of cause-effect, time sequence, or plot elements
    structure_signals = 0
    for kw in ["因为", "所以", "然后", "后来", "突然", "发现", "于是", "最后", "结果",
               "because", "so", "then", "suddenly", "found", "finally", "discovered"]:
        if kw.lower() in text.lower():
            structure_signals += 1
    if structure_signals >= 4:
        struct = 5
    elif structure_signals >= 2:
        struct = 4
    elif structure_signals >= 1:
        struct = 3
    elif len(sentences) >= 2:
        struct = 2
    else:
        struct = 1

    # ── Creativity flags ──
    flags = []
    for kw, flag in [("突然", "unexpected_twist"), ("发现", "logical_consistency"),
                     ("害怕", "emotional_depth"), ("开心", "emotional_depth"),
                     ("好笑", "humor"), ("哈哈", "humor"),
                     ("像", "rich_imagery"), ("仿佛", "rich_imagery"),
                     ("因为", "logical_consistency"), ("所以", "logical_consistency")]:
        if kw in text and flag not in flags:
            flags.append(flag)

    return {
        "vocabulary_richness": vocab,
        "vocabulary_examples": vocab_examples,
        "descriptive_ability": desc,
        "descriptive_examples": desc_examples,
        "story_structure": struct,
        "structure_note": f"程序化评估: {word_count}词, {len(sentences)}句, {structure_signals}个结构信号",
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


class LLMServiceError(Exception):
    pass


# Singleton
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
