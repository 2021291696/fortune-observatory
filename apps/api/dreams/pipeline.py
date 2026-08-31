from __future__ import annotations

from dreams.index import MemoryIndex
from dreams.models import InterpretResponse
from dreams.retrieve import retrieve

REFERRAL = "若睡眠持续被毁、或清醒后仍有自伤/伤人意图，请先寻求专业医疗或危机支持，这里不替代评估。"
LETHAL = ("自杀", "不想活", "结束生命", "了结自己")
UNSAFE = ("反复噩梦", "睡不着", "自伤", "伤自己", "醒来也还想", "伤人")


def _unsafe(text: str) -> bool:
    if any(key in text for key in LETHAL):
        return True
    return sum(1 for key in UNSAFE if key in text) >= 2


def interpret(
    dream: str,
    index: MemoryIndex,
    query_vec: list[float] | None,
    *,
    overlay_text: str | None = None,
) -> InterpretResponse:
    if _unsafe(dream):
        return InterpretResponse(essay="", sources=[], overlay=None, referral=REFERRAL)
    return InterpretResponse(
        essay="",
        sources=retrieve(dream, index, query_vec),
        overlay=overlay_text,
        referral=None,
    )
