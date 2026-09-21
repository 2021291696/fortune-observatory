from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator

import httpx

from ai_explainer import (
    _PROVIDER_RETRY_ATTEMPTS,
    _PROVIDER_RETRY_BASE_SECONDS,
    _read_limited_json_response,
    _retry_provider_status,
    AiConfigurationError,
    AiProviderError,
    get_provider_config,
    reserve_daily_budget,
)
from reading_agent import stream_completion
from tcm.models import ConsultRequest, ConsultResponse, SourceOut
from tcm.prompts import STREAM, system_prompt

logger = logging.getLogger("fortune.tcm")


# 域专用内容红线：解梦/奇门共用 ai_explainer.safety_violation，其 medical 正则
# （服用/剂量类）会拦掉倪师口径的核心产出（方剂剂量煎服法）。中医域改用本表：
# 保留确定性断语与投资红线，另设西药指令红线——经方库不会推荐现代药物，命中
# 说明答案跑偏；中药剂量语言（两/钱/枚）不匹配阿拉伯数字单位，正常放行。
_TCM_SAFETY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("deterministic", r"(?:注定|必然|百分之百|保证你|一定会)"),
    (
        "western_med",
        r"(?:阿司匹林|布洛芬|抗生素|处方药|注射|输液|手术治疗|\d+\s*(?:mg|毫克|片|粒|ml|毫升))",
    ),
    (
        "investment",
        r"(?:购买|买入|卖出|加仓|减仓|满仓|抄底|做多|做空|上杠杆|借贷投资|"
        r"股票|基金|债券|期货|期权|虚拟币|加密货币)",
    ),
)

# 急性危重信号：命中即确定性转介（不打 LLM、不出方），对齐解梦自伤转介的产品口径。
_EMERGENCY_PATTERNS = (
    "心梗", "心肌梗死", "中风", "脑出血", "昏迷", "休克", "大出血", "呕血", "咯血",
    "呼吸困难", "意识不清", "意识模糊", "抽搐不止", "剧烈胸痛", "胸口剧痛", "高热惊厥",
)

# 免责框固定文案（与 skill 口径一致），流式/非流式收尾强校验缺失即补齐。
DISCLAIMER = (
    "⚠️ 本内容仅用于中医学习与学术研究，不构成医疗诊断、处方或个体化治疗建议。"
    "身体不适请咨询执业中医师辨证开方；急性危重症请立即送医。"
)

_REFERRAL_TEXT = (
    "我跟你说，这种情况不能拖——你描述的表现可能是急性危重症，别等中医调养，"
    "也别自己在网上找方子。现在就拨打 120 或直接去急诊，让西医先救命，"
    "稳定了以后再看中医调理，懂了没有？这一条比什么经方都重要。"
)

_ESSAY_CAP = 3600


def safety_violation_tcm(text: str) -> str | None:
    """返回命中的域红线类别名（deterministic/western_med/investment），无命中为 None。"""
    for name, pattern in _TCM_SAFETY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE if name == "western_med" else 0):
            return name
    return None


def is_emergency(question: str) -> bool:
    return any(pattern in question for pattern in _EMERGENCY_PATTERNS)


def _emergency_result() -> ConsultResponse:
    return ConsultResponse(referral=_REFERRAL_TEXT, essay="", sources=[])


def extract_sources(text: str) -> list[SourceOut]:
    """从正文提取《著作》引用与邻近引句（流式收尾用），最多 3 条。"""
    sources: list[SourceOut] = []
    seen: set[str] = set()
    for match in re.finditer(r"《([^《》]{2,20})》", text):
        work = match.group(1).strip()
        if not work or work in seen:
            continue
        window_start = max(0, match.start() - 80)
        window = text[window_start:min(len(text), match.end() + 80)]
        quote_match = re.search(r"[“\"「]([^“”\"」]{6,60})[”\"」]", window)
        if not quote_match:
            continue
        quote = quote_match.group(1).strip().strip('"「」『』【】（）()，。；…—')
        if not quote or quote in seen:
            continue
        seen.add(work)
        seen.add(quote)
        sources.append(SourceOut(work=f"《{work}》", quote=quote))
        if len(sources) >= 3:
            break
    return sources


def _compose_user(question: str) -> str:
    return f"问诊：{question[:2000]}"


def _enforce_disclaimer(essay: str) -> str:
    """免责框缺失即补齐——免责是产品底线，不依赖模型自觉。"""
    if DISCLAIMER in essay:
        return essay
    return f"{essay.rstrip()}\n\n{DISCLAIMER}"


def _provider():
    try:
        return get_provider_config()
    except AiConfigurationError:
        return None


async def _chat(system: str, user: str) -> str:
    config = _provider()
    if config is None:
        raise AiConfigurationError("AI provider is not configured")
    # 倪师口径摘录（2 万+字符）+ 要求出方出剂量，生成耗时高于常规解读，
    # 固定用长超时（50s < RequestGuard 的 62s AI 门，不冲突）。
    timeout_seconds = max(config.timeout_seconds, 50.0)
    timeout = httpx.Timeout(timeout_seconds, connect=min(3.0, timeout_seconds))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        started = time.monotonic()
        response = None
        for attempt in range(_PROVIDER_RETRY_ATTEMPTS):
            response = await client.post(
                f"{config.base_url}/chat/completions",
                headers={
                    "authorization": f"Bearer {config.api_key}",
                    "content-type": "application/json",
                    "accept": "application/json",
                },
                json={
                    "model": config.model,
                    "max_tokens": 4096,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            if _retry_provider_status(response.status_code) and attempt < _PROVIDER_RETRY_ATTEMPTS - 1:
                if time.monotonic() - started > 56.0:
                    logger.warning("tcm provider retry skipped: wall clock exhausted attempt=%s", attempt + 1)
                    break
                logger.warning("tcm provider retryable failure status=%s attempt=%s",
                               response.status_code, attempt + 1)
                await asyncio.sleep(_PROVIDER_RETRY_BASE_SECONDS * (attempt + 1))
                continue
            break
        try:
            response.raise_for_status()
            # provider 响应体与 explain 通道同上限（64KB）后再解析。
            payload = await _read_limited_json_response(response)
            text = str(payload["choices"][0]["message"]["content"] or "").strip()
        except Exception as error:
            raise AiProviderError("tcm consult failed") from error
        return text


async def consult_request(request: ConsultRequest) -> ConsultResponse:
    if is_emergency(request.question):
        return _emergency_result()

    config = _provider()
    if config is None:
        raise AiConfigurationError("AI provider is not configured")
    # 转介路径不消耗 LLM，预算只对真实生成扣（try 外扣，超限抛 429）。
    reserve_daily_budget(config.daily_limit)
    try:
        raw = await _chat(system_prompt(), _compose_user(request.question))
    except (AiConfigurationError, AiProviderError):
        raise
    except Exception as error:
        raise AiProviderError("tcm consult failed") from error
    essay = _enforce_disclaimer(raw.strip())
    if not essay:
        raise AiProviderError("empty essay")
    violation = safety_violation_tcm(essay)
    if violation is not None:
        logger.warning("tcm consult safety violation kind=%s", violation)
        raise AiProviderError(f"tcm consult safety violation: {violation}")
    return ConsultResponse(essay=essay[:_ESSAY_CAP], sources=extract_sources(essay))


async def stream_consult_events(request: ConsultRequest) -> AsyncIterator[dict]:
    """流式问诊：产出 {"type":"delta","text"} 与 {"type":"done","sources":[…]} 事件。"""
    if is_emergency(request.question):
        yield {"type": "delta", "text": _REFERRAL_TEXT}
        yield {"type": "done", "sources": []}
        return
    config = _provider()
    if config is None:
        raise AiConfigurationError("AI provider is not configured")
    reserve_daily_budget(config.daily_limit)

    chunks: list[str] = []
    think_chunks: list[str] = []
    try:
        # stream_completion 产出 (kind, segment) 二元组：思考链转播给前端折叠条，
        # 只有正文 delta 进问诊文本与收尾全文。
        async for kind, text in stream_completion(system=system_prompt(), user=_compose_user(request.question), config=config):
            if kind == "think":
                think_chunks.append(text)
                yield {"type": "think", "text": text}
                continue
            chunks.append(text)
            yield {"type": "delta", "text": text}
    except AiConfigurationError:
        raise
    except AiProviderError:
        raise
    except Exception as error:
        raise AiProviderError("tcm consult failed") from error
    essay = "".join(chunks).strip()
    if not essay:
        raise AiProviderError("empty essay")
    # 域红线收尾校验：正文已流出无法撤回，命中以 error+code=safety 收尾，
    # 前端清空展示层并提示换问法（与非流式的拒绝同口径，只是时机不同）。
    # 思考链同过闸——它也在向用户传输。
    violation = safety_violation_tcm(essay + "".join(think_chunks))
    if violation is not None:
        logger.warning("tcm consult safety violation kind=%s", violation)
        yield {"type": "error", "detail": f"safety violation: {violation}", "code": "safety"}
        return
    # 免责框缺失补齐：补的这段跟随收尾一起流出，保证用户永远看到免责。
    if DISCLAIMER not in essay:
        tail = f"\n\n{DISCLAIMER}"
        chunks.append(tail)
        yield {"type": "delta", "text": tail}
    yield {"type": "done", "sources": [item.model_dump(mode="json") for item in extract_sources("".join(chunks))]}
