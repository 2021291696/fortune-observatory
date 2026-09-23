"""奇门遁甲服务：确定性排盘 + 流式解读。

排盘走 fortune_core.qimen（唯一计算源）；解读复用 reading_agent 的流式补全，
口径来自 skills/qimen-dunjia/references，收尾过 ai_explainer 的安全红线校验。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from ai_explainer import (
    AiConfigurationError,
    AiProviderError,
    get_provider_config,
    reserve_daily_budget,
)
from fortune_core.qimen import build_output
from qimen.lore import skill_profile
from qimen.models import (
    Ganzhi,
    Jieqi,
    LunarDate,
    QimenChartOut,
    QimenChartRequest,
    QimenChartResponse,
    QimenInterpretRequest,
)
from qimen.prompts import INTERPRET_STREAM, SYSTEM
from reading_agent import stream_completion

logger = logging.getLogger("fortune.qimen")

# 引擎警告文案保持与 skill 脚本逐字一致（差分对拍契约），
# CLI 口径的措辞（"脚本""访谈"）只在 API 展示层转网页口径。
_WARNING_REWRITES = (
    ("未提供海外时区，脚本暂按", "未提供海外时区，暂按"),
    ("请在访谈中先补齐时区。", "请在表单里补齐时区。"),
)


def _presentable_warnings(warnings: list[str]) -> list[str]:
    out: list[str] = []
    for text in warnings:
        for old, new in _WARNING_REWRITES:
            text = text.replace(old, new)
        out.append(text)
    return out


def build_qimen_chart(request: QimenChartRequest) -> QimenChartResponse:
    payload = {
        "question_type": request.question_type,
        "question_goal": request.question_goal,
        "time_input": request.time_input,
        "calendar_type": "now" if request.time_mode == "now" else "solar",
        "location": {"country": "", "city": request.city or "", "timezone": ""},
        "ruleset": "mainline-cn-v1",
    }
    try:
        out = build_output(payload)
    except ValueError as error:
        raise ValueError(f"起局信息无法解析：{error}") from error
    return QimenChartResponse(
        question_type=request.question_type,
        question_goal=request.question_goal,
        detail_level=request.detail_level,
        city=request.city or None,
        used_now=bool(out["normalized_input"]["used_now"]),
        calendar_solar=out["calendar"]["solar"]["ymd_hms"],
        calendar_lunar=LunarDate.model_validate(out["calendar"]["lunar"]),
        jieqi=Jieqi.model_validate(out["calendar"]["jieqi"]),
        ganzhi=Ganzhi.model_validate(out["ganzhi"]),
        chart=QimenChartOut.model_validate(out["chart"]),
        warnings=_presentable_warnings(out["warnings"]),
    )


def _interpret_user(chart: QimenChartResponse) -> str:
    facts = {
        "事项类型": chart.question_type,
        "判断目标": chart.question_goal,
        "输出偏好": "直接结论" if chart.detail_level == "brief" else "详细讲解",
        "起局时间（公历）": chart.calendar_solar,
        "城市": chart.city or "未填写（按北京时间起局）",
        "规则集": "mainline-cn-v1（时家转盘奇门）",
        "盘面数据": {
            "ganzhi": chart.ganzhi.model_dump(),
            "chart": chart.chart.model_dump(),
        },
    }
    return json.dumps(facts, ensure_ascii=False) + "\n\n" + INTERPRET_STREAM


def _provider():
    try:
        return get_provider_config()
    except AiConfigurationError:
        return None


async def stream_qimen_events(request: QimenInterpretRequest) -> AsyncIterator[dict]:
    """流式奇门解读：产出 {"type":"delta","text"} / {"type":"think","text"} / {"type":"done"} 事件。"""
    config = _provider()
    if config is None:
        raise AiConfigurationError("AI provider is not configured")
    # 预算只对真实生成扣（try 外扣，超限抛 429 由端点映射）。
    reserve_daily_budget(config.daily_limit)
    profile = skill_profile()
    system = f"{SYSTEM}\n\n{profile}" if profile else SYSTEM
    user = _interpret_user(request.chart)

    chunks: list[str] = []
    think_chunks: list[str] = []
    try:
        async for kind, text in stream_completion(system=system, user=user, config=config):
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
        raise AiProviderError("qimen essay failed") from error
    essay = "".join(chunks).strip()
    if not essay:
        raise AiProviderError("empty essay")
    yield {"type": "done"}
