from __future__ import annotations

import json
import logging
import re

import httpx
from fastapi import HTTPException

from ai_explainer import AiConfigurationError, AiExplainRequest, AiProviderError, get_provider_config, _verified_facts
from dreams.lore import _WORK_TITLES, skill_profile
from dreams.models import InterpretRequest, InterpretResponse, QuestionOut, QuestionsResponse, SourceOut
from dreams.prompts import INTERPRET_JSON, QUESTIONS, SYSTEM

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
    timeout = httpx.Timeout(config.timeout_seconds, connect=min(3.0, config.timeout_seconds))
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
        essay = text.strip()
    if not essay:
        raise AiProviderError("empty essay")
    return InterpretResponse(essay=essay[:3600], sources=sources[:3])


async def interpret_dream_request(request: InterpretRequest) -> InterpretResponse:
    if any(pattern in request.dream for pattern in _REFERRAL_PATTERNS):
        return _referral_result(request.dream)

    overlay_text = None
    if request.overlay and request.context_tokens:
        config = _provider()
        if config is not None:
            try:
                facts = _verified_facts(
                    AiExplainRequest(question=request.dream[:300], context_tokens=request.context_tokens),
                    config.context_secret,
                )
                overlay_text = "；".join(fact.text for fact in facts)
            except Exception as error:
                raise HTTPException(status_code=422, detail="对照命盘上下文无效。") from error

    profile = skill_profile()
    system = f"{SYSTEM}\n\n{profile}" if profile else SYSTEM
    lines = [f"梦：{request.dream[:2000]}"]
    extra = [f"{item.question}：{item.answer}" for item in request.answers if item.answer]
    if extra:
        lines.append("补充：\n" + "\n".join(extra))
    if overlay_text:
        lines.append(f"命盘摘要：{overlay_text[:400]}")
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
