"""紫微/八字分开解读：运势八字语境、单体系上下文组合、体系提示词选型。"""

from datetime import date, datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from ai_explainer import (
    AiExplainRequest,
    AiFact,
    build_signed_context,
    verified_reading_context,
)
from app import create_chart, create_daily_transit, create_transit_window
from fortune_core.models import BirthInput, DailyTransitRequest, TransitWindowRequest
from reading_agent import build_reading_system

SECRET = "context-signing-secret-that-is-long-enough"
GROUP = "group-abcdefgh"


def _birth() -> BirthInput:
    return BirthInput(
        civil_datetime=datetime.fromisoformat("1995-06-15T08:30:00+08:00"),
        timezone_id="Asia/Shanghai",
        longitude=116.4074,
        latitude=39.9042,
        sex_for_rule="male",
    )


def test_domain_contexts_are_single_system_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    """领域语境包只收紫微口径：不得混入七政锚点或八字日主锚点。"""
    monkeypatch.setenv("FORTUNE_AI_CONTEXT_SECRET", SECRET)
    result = create_chart(_birth())
    for domain in ("health", "relationship", "career", "wealth"):
        bundle = result.ai_contexts.get(domain)
        assert bundle is not None, domain
        texts = [fact.text for fact in bundle.facts]
        assert all("七政" not in text for text in texts), (domain, texts)
        assert all("日主" not in text for text in texts), (domain, texts)
        # 领域包仍须保留紫微宫位事实（本宫/对宫/三合/大限）。
        assert any("宫" in text for text in texts), (domain, texts)


def test_daily_returns_bazi_context_for_verified_birth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORTUNE_AI_CONTEXT_SECRET", SECRET)
    result = create_daily_transit(DailyTransitRequest(birth=_birth(), transit_date=date(2026, 9, 2)))
    bundle = result.ai_context_bazi
    assert bundle is not None
    texts = [fact.text for fact in bundle.facts]
    assert any("四柱（子平排盘）" in text for text in texts)
    assert any("大运" in text for text in texts)
    assert any(text.startswith("流年：") and "流年干" in text for text in texts)
    assert any(text.startswith("流日：") for text in texts)
    # 八字节事实不得混入紫微术语
    assert all("四化" not in text and "宫" not in text for text in texts)


def test_window_returns_bazi_context_for_verified_birth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORTUNE_AI_CONTEXT_SECRET", SECRET)
    result = create_transit_window(
        TransitWindowRequest(birth=_birth(), start_date=date(2026, 8, 31), end_date=date(2026, 9, 6))
    )
    bundle = result.ai_context_bazi
    assert bundle is not None
    texts = [fact.text for fact in bundle.facts]
    assert any("四柱（子平排盘）" in text for text in texts)
    assert any("时间范围" in text and "地支关系" in text for text in texts)


def test_single_core_context_combination_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """分开解读的组合形态：领域宫 + 恰好一个体系排盘（紫微侧）。"""
    monkeypatch.setenv("FORTUNE_AI_CONTEXT_SECRET", SECRET)
    ziwei = build_signed_context(
        "domain", [AiFact(id="z-1", text="命宫在寅")],
        bundle_type="ziwei.chart", context_group=GROUP,
    )
    request = AiExplainRequest(question="批解姻缘", context_tokens=[ziwei.token])
    facts, bundle_types = verified_reading_context(request, SECRET.encode())
    assert bundle_types == {"ziwei.chart"}
    assert facts


def test_single_bazi_context_alone_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORTUNE_AI_CONTEXT_SECRET", SECRET)
    bazi = build_signed_context(
        "fortune", [AiFact(id="b-1", text="日主丁火，当前大运己卯")],
        bundle_type="bazi.chart", context_group=GROUP,
    )
    request = AiExplainRequest(question="今日运势", context_tokens=[bazi.token])
    facts, bundle_types = verified_reading_context(request, SECRET.encode())
    assert bundle_types == {"bazi.chart"}
    assert facts


def test_mixed_fortune_and_chart_context_still_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORTUNE_AI_CONTEXT_SECRET", SECRET)
    fortune = build_signed_context(
        "fortune", [AiFact(id="f-1", text="流日乙亥")],
        bundle_type="fortune.daily", context_group=GROUP,
    )
    ziwei = build_signed_context(
        "domain", [AiFact(id="z-1", text="命宫在寅")],
        bundle_type="ziwei.chart", context_group=GROUP,
    )
    request = AiExplainRequest(question="解读", context_tokens=[fortune.token, ziwei.token])
    with pytest.raises(Exception):
        verified_reading_context(request, SECRET.encode())


def test_reading_system_selects_single_system_corpus_and_terms() -> None:
    ziwei_sys = build_reading_system({"ziwei.chart"})
    bazi_sys = build_reading_system({"bazi.chart"})
    combined_sys = build_reading_system({"ziwei.chart", "bazi.chart"})
    daily_ziwei_sys = build_reading_system({"fortune.daily"})

    assert "只用紫微斗数术语" in ziwei_sys and "双体系合参" not in ziwei_sys
    assert "ziwei-doushu/SKILL.md" in ziwei_sys and "bazi/references" not in ziwei_sys
    assert "只用八字术语" in bazi_sys and "双体系合参" not in bazi_sys
    assert "bazi/references/classical-texts.md" in bazi_sys and "ziwei-doushu" not in bazi_sys
    assert "双体系合参" in combined_sys
    assert "ziwei-doushu/SKILL.md" in combined_sys and "bazi/references" in combined_sys
    assert "只用紫微斗数术语" in daily_ziwei_sys and "ziwei-doushu/SKILL.md" in daily_ziwei_sys
