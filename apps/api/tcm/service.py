from __future__ import annotations

import asyncio
import logging
import re
import time
import unicodedata
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
# 说明答案跑偏；中药剂量语言（两/钱/枚）不匹配数字+片/粒/毫克单位，正常放行。
# 词表按「词族/口语同义族」收，不点名单词——点名单词每漏一个口语面就漏一道闸
# （run-3 实测：阿莫西林/头孢/两粒/根治/定投 当时全部零触发）。
_TCM_SAFETY_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "deterministic",
        r"(?:注定|必然|百分之百|保证你|一定会|一定能|绝对能|根治|断根|包你|药到病除)",
    ),
    (
        "western_med",
        # 药名按类收（*西林/*头孢/*霉素 覆盖整类译名药）；数量词含中文数字
        # （两粒/半片）。单位只列片/粒/mg/毫克/ml/毫升——中药剂量的两/钱/枚/升
        # 不入列；片/粒 计数按既有产品立场一律按西药剂量语言处理
        # （test_western_med_blocked 钉死「每天3片」）。
        r"(?:阿司匹林|布洛芬|对乙酰氨基酚|扑热息痛|止疼药|止痛药|退烧药|退热药"
        r"|抗生素|处方药|注射|输液|手术治疗"
        r"|(?:[0-9]+|[一两二三四五六七八九十百千几半]+)\s*"
        r"(?:mg|毫克|片|粒|ml|毫升)"
        r"|西林|头孢|霉素)",
    ),
    (
        "investment",
        r"(?:购买|买入|卖出|加仓|减仓|满仓|抄底|做多|做空|上杠杆|借贷投资|"
        r"股票|基金|债券|期货|期权|虚拟币|加密货币|买点|建仓|定投|炒币)",
    ),
)

# 急性危重信号：命中即确定性转介（不打 LLM、不出方），对齐解梦自伤转介的产品口径。
# 同义词族收全口语面（run-3 实测：心肌梗塞/脑梗/脑卒中/吐血/抽搐/喘不上气 全漏）；
# 匹配前先规范化（is_emergency），防拆字/零宽/全角绕闸。
_EMERGENCY_PATTERNS = (
    "心梗", "心肌梗死", "心肌梗塞", "心绞痛",
    "中风", "脑梗", "脑梗死", "脑梗塞", "脑卒中", "脑出血", "脑溢血",
    "昏迷", "昏厥", "晕厥", "休克",
    "大出血", "呕血", "咯血", "吐血",
    "呼吸困难", "喘不上气", "喘不过气",
    "意识不清", "意识模糊", "抽搐", "高热惊厥", "高烧惊厥",
    "剧烈胸痛", "胸口剧痛",
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


# 零宽字符（ZWSP/ZWNJ/ZWJ/WJ/BOM）显式按码点构造：源码保持纯 ASCII，
# 防格式化器把字面量零宽字符剥掉后正则悄悄失效。
_INVISIBLE_CHARS = re.compile(r"[\s" + "".join(map(chr, (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF))) + "]+")


def _normalize_signal_text(text: str) -> str:
    """信号匹配前规范化：NFKC 折叠全角/兼容字符，剥掉空白与零宽字符，
    否则「心肌 梗塞」「脑<零宽>梗」这类拆字写法能绕开子串匹配。"""
    return _INVISIBLE_CHARS.sub("", unicodedata.normalize("NFKC", text))


def is_emergency(question: str) -> bool:
    normalized = _normalize_signal_text(question)
    return any(_normalize_signal_text(pattern) in normalized for pattern in _EMERGENCY_PATTERNS)


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


def _fit_essay(raw: str) -> str:
    """先裁后补：正文裁进「_ESSAY_CAP − 免责框」的预算位，免责框强制落在结尾。

    顺序是产品底线（保证用户永远看到免责）：此前 enforce 在 [:_ESSAY_CAP] 截断
    之前跑，长文会把结尾的免责框切掉。模型自带的结尾免责先剥掉再补，避免双份。
    """
    body = raw.strip()
    head = body[: -len(DISCLAIMER)].rstrip() if body.endswith(DISCLAIMER) else body.rstrip()
    room = _ESSAY_CAP - len(DISCLAIMER) - 2
    return f"{head[:room].rstrip()}\n\n{DISCLAIMER}"


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
    if not raw.strip():
        raise AiProviderError("empty essay")
    # 红线过全文（与修复前同口径），截断只影响交付形态、不影响放行判定。
    violation = safety_violation_tcm(raw.strip())
    if violation is not None:
        logger.warning("tcm consult safety violation kind=%s", violation)
        raise AiProviderError(f"tcm consult safety violation: {violation}")
    essay = _fit_essay(raw)
    return ConsultResponse(essay=essay, sources=extract_sources(essay))


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
    # 与非流式「先裁后补」同口径：正文裁进预算位，免责框强制结尾。
    relayed = 0
    essay_budget = _ESSAY_CAP - len(DISCLAIMER) - 2
    try:
        # stream_completion 产出 (kind, segment) 二元组：思考链转播给前端折叠条，
        # 只有正文 delta 进问诊文本与收尾全文。
        async for kind, text in stream_completion(system=system_prompt(), user=_compose_user(request.question), config=config):
            if kind == "think":
                think_chunks.append(text)
                yield {"type": "think", "text": text}
                continue
            if relayed + len(text) > essay_budget:
                continue
            relayed += len(text)
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
