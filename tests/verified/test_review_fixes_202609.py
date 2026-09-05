"""2026-09-05 审查修复的回归：转介绕过、reading 预算 429、fact 截断、北京口径。

此前问题：
- is_referral 只查梦正文，追问回答可绕过自伤转介；
- /v1/ai/reading 预算耗尽裸抛 AiBudgetExceeded → 全局 500（应 429 + Retry-After）；
- 问事/紫微等 AI 语境 fact 未截 400 字，超高龄出生的"已过大限"长行撑爆 AiFact → 排盘 500；
- 预算日切与 Retry-After 按 UTC（凌晨语义错位），现按北京时间。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import app as app_module
from ai_explainer import AiBudgetExceeded, seconds_until_budget_reset
from dreams.models import ComplexAnswer
from dreams.service import is_referral


def test_is_referral_covers_answers():
    assert is_referral("我想自杀") is True
    # 正文干净、追问里透露信号：此前可绕过转介直进 LLM
    assert is_referral("梦见朋友生病住院") is False
    assert is_referral("梦见朋友生病住院", [
        ComplexAnswer(id="fear_of", question="最怕的是哪一幕？", answer="怕他轻生"),
    ]) is True
    assert is_referral("梦见朋友生病住院", [
        ComplexAnswer(id="fear_of", question="最怕的是哪一幕？", answer="怕他出不了院"),
    ]) is False


def test_seconds_until_budget_reset_bounds():
    value = seconds_until_budget_reset()
    assert 60 <= value <= 86_400


_BIRTH = {
    "civil_datetime": "1901-06-15T10:30:00+08:00",
    "timezone_id": "Asia/Shanghai",
    "longitude": 120.15,
    "latitude": 30.28,
    "sex_for_rule": "male",
    "use_apparent_solar_time": True,
}


def test_chart_facts_truncated_for_oldest_births(monkeypatch):
    """1901 年出生（+08:00 口径下最早可提交的年份）虚岁 126，"已过大限"长行
    此前未截断会撑爆 AiFact(400) 使排盘 500；现在必须 200 且所有 fact ≤400 字。"""
    monkeypatch.setenv("FORTUNE_AI_CONTEXT_SECRET", "x" * 48)
    client = TestClient(app_module.app)
    response = client.post("/v1/charts", json=_BIRTH)
    assert response.status_code == 200, response.text
    bundles = response.json()["ai_contexts"]
    assert bundles, "配置了签名密钥时应返回 AI 语境包"
    for bundle in bundles.values():
        if not bundle:
            continue
        for fact in bundle["facts"]:
            assert len(fact["text"]) <= 400


def test_reading_budget_exceeded_returns_429_not_500(monkeypatch):
    """预算扣减此前在 try 外裸抛：/v1/ai/reading 额度用完返回 500。
    钉住 429 + Retry-After + 中文提示。"""
    from ai_explainer import AiConfigurationError  # noqa: F401  # 确认异常族可导入

    class _FakeConfig:
        context_secret = b"s" * 32
        daily_limit = 10

    monkeypatch.setattr(app_module, "get_provider_config", lambda: _FakeConfig())
    monkeypatch.setattr(app_module, "verified_reading_context", lambda request, secret: ([], set()))

    def boom(_limit):
        raise AiBudgetExceeded("AI daily request budget exhausted")

    monkeypatch.setattr(app_module, "reserve_daily_budget", boom)

    client = TestClient(app_module.app)
    response = client.post("/v1/ai/reading", json={
        "question": "结合命盘讲讲当前阶段",
        "context_tokens": ["t" * 32],
        "stream_key": "test-budget-key-01",
    })
    assert response.status_code == 429, response.text
    assert "额度已用完" in response.json()["detail"]
    assert int(response.headers["retry-after"]) >= 60


def test_dreams_interpret_rejects_unclean_answers_via_route(monkeypatch):
    """路由级钉住：转介命中时返回 referral 且不调用 LLM（预算不被扣）。"""
    monkeypatch.setenv("FORTUNE_AI_CONTEXT_SECRET", "x" * 48)
    charged: list[int] = []
    monkeypatch.setattr(app_module, "reserve_daily_budget", lambda limit: charged.append(limit))
    client = TestClient(app_module.app)
    response = client.post("/v1/dreams/interpret", json={
        "dream": "梦见朋友生病住院",
        "mode": "complex",
        "answers": [
            {"id": "fear_of", "question": "最怕的是哪一幕？", "answer": "怕他轻生"},
        ],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["referral"], "追问里透露自伤信号必须转介"
    assert charged == [], "转介路径不得扣预算"
    dumped = json.dumps(body, ensure_ascii=False)
    assert "伤害自己" in dumped and "心理援助" in dumped
