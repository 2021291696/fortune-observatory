from __future__ import annotations

import json
import logging
import re

import httpx
from fastapi import HTTPException

from ai_explainer import AiConfigurationError, AiExplainRequest, AiProviderError, get_provider_config, _verified_facts
from dreams.embed import embed_texts
from dreams.index import MemoryIndex
from dreams.loader import load_records
from dreams.store import load_store
from dreams.models import InterpretRequest, InterpretResponse, QuestionOut, QuestionsResponse
from dreams.pipeline import interpret
from dreams.prompts import QUESTIONS, SYSTEM

logger = logging.getLogger("fortune.dreams")


_index: MemoryIndex | None = None
_REQUIRED_IDS = ("finished", "agency", "fear_of")


def get_index() -> MemoryIndex:
    global _index
    if _index is None:
        stored = load_store()
        if stored is not None:
            records, vectors = stored
        else:
            records = load_records()
            vectors = embed_texts([record.text for record in records], kind="db")
        _index = MemoryIndex(records, vectors)
    return _index


def compose_query(dream: str, answers: list[ComplexAnswer]) -> str:
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


def _essay_user(dream: str, result: InterpretResponse, overlay_text: str | None) -> str:
    refs = "\n".join(
        f"- [{item.channel}] {item.work}：{item.quote}" for item in result.sources
    ) or "（无匹配）"
    lines = [f"梦：{dream[:2000]}", f"参考：\n{refs}"]
    if overlay_text:
        lines.append(f"命盘摘要：{overlay_text[:400]}")
    return "\n".join(lines)


async def write_essay(dream: str, result: InterpretResponse, overlay_text: str | None) -> InterpretResponse:
    if result.referral:
        return result
    if _provider() is None:
        raise AiConfigurationError("AI provider is not configured")
    try:
        essay = await _chat(SYSTEM, _essay_user(dream, result, overlay_text))
    except AiConfigurationError:
        raise
    except AiProviderError:
        raise
    except Exception as error:
        raise AiProviderError("dream essay failed") from error
    if not essay.strip():
        raise AiProviderError("empty essay")
    return result.model_copy(update={"essay": essay})


async def interpret_dream_request(request: InterpretRequest) -> InterpretResponse:
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
    index = get_index()
    try:
        query_vec = embed_texts([request.dream], kind="query")[0]
    except Exception as error:
        logger.warning("dream embed skipped error_type=%s", type(error).__name__)
        query_vec = None
    result = interpret(request.dream, index, query_vec, overlay_text=overlay_text)
    return await write_essay(request.dream, result, overlay_text)
