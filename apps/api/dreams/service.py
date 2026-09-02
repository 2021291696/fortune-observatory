from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator

import httpx

from ai_explainer import AiConfigurationError, AiProviderError, get_provider_config
from dreams.lore import _WORK_TITLES, skill_profile
from dreams.models import InterpretRequest, InterpretResponse, QuestionOut, QuestionsResponse, SourceOut
from dreams.prompts import INTERPRET_JSON, QUESTIONS, SYSTEM
from reading_agent import stream_completion

logger = logging.getLogger("fortune.dreams")


_REQUIRED_IDS = ("finished", "agency", "fear_of")
# 触发转介的自伤信号：只依据梦的明确叙述，不做推断
_REFERRAL_PATTERNS = ("自杀", "轻生", "不想活", "伤害自己", "伤自己", "自残")


def compose_query(dream: str, answers: list) -> str:
    extra = [f"{item.question}：{item.answer}" for item in answers if item.answer]
    return "\n".join([dream, *extra]) if extra else dream


def heuristic_questions(dream: str) -> list[QuestionOut]:
    snippet = re.sub(r"\s+", "", dream)[:16] or "这场梦"
    return [
        QuestionOut(id="finished", label=f"「{snippet}」做到结尾了吗？"),
        QuestionOut(id="agency", label="走进这个场面，是你自己要去，还是被卷进去的？"),
        QuestionOut(id="fear_of", label="最怕的是哪一幕，或哪个人？"),
    ]


def _parse_questions(text: str) -> list[QuestionOut]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no json")
    payload = json.loads(text[start:end + 1])
    raw = payload.get("questions")
    if not isinstance(raw, list):
        raise ValueError("no questions")
    by_id = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id") or "")
        label = str(item.get("label") or "").strip()[:80]
        if qid in _REQUIRED_IDS and label:
            by_id[qid] = QuestionOut(id=qid, label=label)
    return [by_id[qid] for qid in _REQUIRED_IDS if qid in by_id]


def _provider():
    try:
        return get_provider_config()
    except AiConfigurationError:
        return None


async def _chat(system: str, user: str) -> str:
    config = _provider()
    if config is None:
        raise AiConfigurationError("AI provider is not configured")
    # 解梦 prompt 含全量 skill 口径（4 万+字符），生成耗时显著高于常规解读，
    # 固定用长超时；config.timeout_seconds 被 28 秒级网关约束，这里不受其限。
    timeout_seconds = max(config.timeout_seconds, 50.0)
    timeout = httpx.Timeout(timeout_seconds, connect=min(3.0, timeout_seconds))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        response = await client.post(
            f"{config.base_url}/chat/completions",
            headers={
                "authorization": f"Bearer {config.api_key}",
                "content-type": "application/json",
                "accept": "application/json",
            },
            json={
                "model": config.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        try:
            response.raise_for_status()
            text = str(response.json()["choices"][0]["message"]["content"] or "").strip()
        except Exception as error:
            raise AiProviderError("dream essay failed") from error
        return text


async def generate_questions(dream: str) -> QuestionsResponse:
    if _provider() is None:
        return QuestionsResponse(questions=heuristic_questions(dream))
    try:
        questions = _parse_questions(await _chat(QUESTIONS, dream[:800]))
        if len(questions) < 3:
            raise ValueError("incomplete")
        return QuestionsResponse(questions=questions)
    except Exception as error:
        logger.warning("dream questions fallback error_type=%s", type(error).__name__)
        return QuestionsResponse(questions=heuristic_questions(dream))


def _referral_result(dream: str) -> InterpretResponse:
    return InterpretResponse(
        referral="这场梦提到了伤害自己。梦不等于现实意图，但如果这些念头在醒来后还在，"
                 "建议找信得过的人或专业的心理援助聊一聊——这一步比任何解梦都重要。",
    )


def _parse_interpret(text: str, dream: str) -> InterpretResponse:
    start = text.find("{")
    end = text.rfind("}")
    sources: list[SourceOut] = []
    essay = ""
    if start >= 0 and end > start:
        try:
            payload = json.loads(text[start:end + 1])
            essay = str(payload.get("essay") or "").strip()
            for item in payload.get("sources") or []:
                if not isinstance(item, dict):
                    continue
                work = str(item.get("work") or "").strip()
                quote = str(item.get("quote") or "").strip()[:80]
                if work in _WORK_TITLES.values() and quote:
                    sources.append(SourceOut(work=work, quote=quote, channel="字面"))
        except ValueError:
            essay = ""
    if not essay:
        # 模型未按 JSON 回包时降级取正文；先从全文兜底提取口径引用，再剥掉 sources 段与前缀
        for work in _WORK_TITLES.values():
            hit = re.search(re.escape(work) + r".{0,24}?quote[\"：:]\s*[\"「『]?([^\"「」『』】）)\n]{6,60})", text)
            if hit:
                quote = hit.group(1).strip().strip('"「」『』【】（）()，。；')
                if quote and not quote.startswith("quote"):
                    sources.append(SourceOut(work=work, quote=quote[:60], channel="近邻"))
        essay = text.strip()
        for prefix in ("解梦正文：", "解梦正文:", "正文：", "正文:"):
            if essay.startswith(prefix):
                essay = essay[len(prefix):]
        marker = re.search(r"\s*sources\s*[:：]", essay)
        if marker:
            essay = essay[:marker.start()]
    essay = essay.strip().strip('"')
    if not essay:
        raise AiProviderError("empty essay")
    return InterpretResponse(essay=essay[:3600], sources=sources[:3])


def extract_sources(text: str) -> list[SourceOut]:
    """从自由文本正文提取《著作》引用与邻近引句（流式收尾用）。

    模型按提示词在正文中引用口径著作（书名号 + 引句），这里扫全文抓
    书名号条目，并在前后窗口内找成对引句；最多 3 条，去重。
    """
    sources: list[SourceOut] = []
    seen_works: set[str] = set()
    for match in re.finditer(r"《([^《》]{2,20})》", text):
        work = match.group(1).strip()
        if not work or work in seen_works:
            continue
        window_start = max(0, match.start() - 80)
        window = text[window_start:min(len(text), match.end() + 80)]
        quote_match = re.search(r"[“\"「]([^“”\"」]{6,60})[”\"」]", window)
        if not quote_match:
            continue
        quote = quote_match.group(1).strip().strip('"「」『』【】（）()，。；…—')
        if not quote or quote in seen_works:
            continue
        seen_works.add(work)
        seen_works.add(quote)
        sources.append(SourceOut(work=f"《{work}》", quote=quote, channel="近邻"))
        if len(sources) >= 3:
            break
    return sources


async def interpret_dream_request(request: InterpretRequest) -> InterpretResponse:
    if any(pattern in request.dream for pattern in _REFERRAL_PATTERNS):
        return _referral_result(request.dream)

    profile = skill_profile()
    system = f"{SYSTEM}\n\n{profile}" if profile else SYSTEM
    lines = [f"梦：{request.dream[:2000]}"]
    extra = [f"{item.question}：{item.answer}" for item in request.answers if item.answer]
    if extra:
        lines.append("补充：\n" + "\n".join(extra))
    lines.append(INTERPRET_JSON)

    if _provider() is None:
        raise AiConfigurationError("AI provider is not configured")
    try:
        raw = await _chat(system, "\n".join(lines))
    except AiConfigurationError:
        raise
    except AiProviderError:
        raise
    except Exception as error:
        raise AiProviderError("dream essay failed") from error
    return _parse_interpret(raw, request.dream)


# 流式版：不再要求 JSON 回包，直接输出解梦正文；引用来源在收尾时后端提取。
_INTERPRET_STREAM = (
    "直接输出解梦正文（Markdown 分节书写），不要 JSON、不要代码块。"
    "行文中引用口径著作时明确写出书名与原句（如《梦的解析》），先引原句再讲白话。"
    "结尾固定两节：「## 可以先做」（2-3 条具体、可执行的动作）与「## 注意」（1 条单句提醒）。"
)


async def stream_interpret_events(request: InterpretRequest) -> AsyncIterator[dict]:
    """流式解梦：产出 {"type":"delta","text"} 与 {"type":"done","sources":[…]} 事件。"""
    if any(pattern in request.dream for pattern in _REFERRAL_PATTERNS):
        yield {"type": "delta", "text": _referral_result(request.dream).referral}
        yield {"type": "done", "sources": []}
        return
    config = _provider()
    if config is None:
        raise AiConfigurationError("AI provider is not configured")
    profile = skill_profile()
    system = f"{SYSTEM}\n\n{profile}" if profile else SYSTEM
    lines = [f"梦：{request.dream[:2000]}"]
    extra = [f"{item.question}：{item.answer}" for item in request.answers if item.answer]
    if extra:
        lines.append("补充：\n" + "\n".join(extra))
    lines.append(_INTERPRET_STREAM)

    chunks: list[str] = []
    try:
        async for delta in stream_completion(system=system, user="\n".join(lines), config=config):
            chunks.append(delta)
            yield {"type": "delta", "text": delta}
    except AiConfigurationError:
        raise
    except AiProviderError:
        raise
    except Exception as error:
        raise AiProviderError("dream essay failed") from error
    essay = "".join(chunks).strip()
    if not essay:
        raise AiProviderError("empty essay")
    yield {"type": "done", "sources": [item.model_dump(mode="json") for item in extract_sources(essay)]}
