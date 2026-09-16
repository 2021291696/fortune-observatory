"""奇门端点与解读服务契约测试（provider 全 mock，零真实配额）。"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import app as api_module
from ai_explainer import AiBudgetExceeded, AiConfigurationError
from qimen.models import QimenInterpretRequest
from qimen.service import _presentable_warnings, stream_qimen_events

CHART_BODY = {
    "question_type": "事业",
    "question_goal": "能不能动，什么时候动更稳",
    "time_mode": "custom",
    "time_input": "2026-03-24 10:30",
    "city": "上海",
}


def _collect_events(request: QimenInterpretRequest) -> list[dict]:
    async def run() -> list[dict]:
        return [event async for event in stream_qimen_events(request)]

    return asyncio.run(run())


def _client() -> TestClient:
    return TestClient(api_module.app)


def _parse_sse(text: str) -> list[dict]:
    events: list[dict] = []
    for line in text.splitlines():
        if line.startswith("data: ") and line != "data: [DONE]":
            events.append(json.loads(line[len("data: "):]))
    return events


def test_qimen_chart_deterministic_fields() -> None:
    res = _client().post("/v1/qimen/chart", json=CHART_BODY)
    assert res.status_code == 200
    body = res.json()
    # 与差分基线（skills/qimen-dunjia references/examples.md 示例 1）一致
    assert body["chart"]["dun_type"] == "阳遁"
    assert body["chart"]["ju_number"] == 1
    assert body["chart"]["xunshou"] == "甲辰"
    assert body["chart"]["hidden_yi"] == "壬"
    assert body["chart"]["zhifu"]["star"] == "天芮"
    assert body["chart"]["zhishi"]["door"] == "死门"
    assert body["ganzhi"]["day"] == "丁酉"
    assert body["used_now"] is False
    assert body["jieqi"]["active_jie"]
    assert len(body["chart"]["palaces"]) == 9
    assert "题" not in body  # 契约外字段不出现


def test_qimen_chart_now_mode() -> None:
    res = _client().post("/v1/qimen/chart", json={
        "question_type": "出行", "question_goal": "今天往哪边走顺",
        "time_mode": "now",
    })
    assert res.status_code == 200
    assert res.json()["used_now"] is True


def test_qimen_chart_validation() -> None:
    client = _client()
    # 非法事项类型
    res = client.post("/v1/qimen/chart", json={"question_type": "玄学", "question_goal": "测试", "time_mode": "now"})
    assert res.status_code == 422
    # 自定义模式缺时间
    res = client.post("/v1/qimen/chart", json={"question_type": "事业", "question_goal": "测试", "time_mode": "custom"})
    assert res.status_code == 422
    # 无法解析的时间
    res = client.post("/v1/qimen/chart", json={
        "question_type": "事业", "question_goal": "测试",
        "time_mode": "custom", "time_input": "三月二十四号",
    })
    assert res.status_code == 422
    # 目标太短
    res = client.post("/v1/qimen/chart", json={"question_type": "事业", "question_goal": "成", "time_mode": "now"})
    assert res.status_code == 422
    # 契约外字段拒绝
    res = client.post("/v1/qimen/chart", json={**CHART_BODY, "overlay": True})
    assert res.status_code == 422


def test_qimen_stream_happy_path(monkeypatch) -> None:
    async def fake_stream(request: QimenInterpretRequest) -> AsyncIterator[dict]:
        assert request.chart.chart.ju_number == 1
        yield {"type": "think", "text": "思考中"}
        yield {"type": "delta", "text": "阳遁一局"}
        yield {"type": "delta", "text": "，可以缓动。"}
        yield {"type": "done"}

    monkeypatch.setattr(api_module, "stream_qimen_events", fake_stream)
    chart = _client().post("/v1/qimen/chart", json=CHART_BODY).json()
    res = _client().post("/v1/qimen/interpret/stream", json={"chart": chart})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(res.text)
    assert events[0] == {"type": "think", "text": "思考中"}
    assert [e["text"] for e in events if e["type"] == "delta"] == ["阳遁一局", "，可以缓动。"]
    assert events[-1] == {"type": "done"}


def test_qimen_stream_safety_and_budget(monkeypatch) -> None:
    async def fake_safety(request: QimenInterpretRequest) -> AsyncIterator[dict]:
        yield {"type": "delta", "text": "…"}
        yield {"type": "error", "detail": "safety violation: deterministic", "code": "safety"}

    monkeypatch.setattr(api_module, "stream_qimen_events", fake_safety)
    chart = _client().post("/v1/qimen/chart", json=CHART_BODY).json()
    res = _client().post("/v1/qimen/interpret/stream", json={"chart": chart})
    events = _parse_sse(res.text)
    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "safety"
    assert "输出规范" in events[-1]["detail"]

    async def fake_budget(request: QimenInterpretRequest) -> AsyncIterator[dict]:
        raise AiBudgetExceeded("daily budget exhausted")
        yield  # pragma: no cover

    monkeypatch.setattr(api_module, "stream_qimen_events", fake_budget)
    res = _client().post("/v1/qimen/interpret/stream", json={"chart": chart})
    events = _parse_sse(res.text)
    assert events[-1]["type"] == "error"
    assert "额度" in events[-1]["detail"]


def test_stream_qimen_events_aggregates_and_safety(monkeypatch) -> None:
    from qimen import service as qimen_service

    class _Config:
        daily_limit = 100

    monkeypatch.setattr(qimen_service, "_provider", lambda: _Config())
    monkeypatch.setattr(qimen_service, "reserve_daily_budget", lambda *_: None)

    async def fake_completion(**_kwargs) -> AsyncIterator[tuple[str, str]]:
        yield ("think", "盘面已读")
        yield ("delta", "结论是")
        yield ("delta", "可以缓动。")

    monkeypatch.setattr(qimen_service, "stream_completion", fake_completion)
    request = QimenInterpretRequest.model_validate({"chart": _client().post("/v1/qimen/chart", json=CHART_BODY).json()})
    events = _collect_events(request)
    assert events[0] == {"type": "think", "text": "盘面已读"}
    assert events[-1] == {"type": "done"}

    async def fake_deterministic(**_kwargs) -> AsyncIterator[tuple[str, str]]:
        yield ("delta", "这事一定会成，闭眼冲。")

    monkeypatch.setattr(qimen_service, "stream_completion", fake_deterministic)
    events = _collect_events(request)
    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "safety"


def test_stream_qimen_events_without_provider(monkeypatch) -> None:
    from qimen import service as qimen_service

    def _no_provider():
        raise AiConfigurationError("not configured")

    monkeypatch.setattr(qimen_service, "_provider", _no_provider)
    request = QimenInterpretRequest.model_validate({"chart": _client().post("/v1/qimen/chart", json=CHART_BODY).json()})
    with pytest.raises(AiConfigurationError):
        _collect_events(request)


def test_presentable_warnings_rewrites_cli_wording() -> None:
    rewritten = _presentable_warnings([
        "未提供海外时区，脚本暂按 Asia/Shanghai 计算，请在访谈中先补齐时区。",
        "本规则集中宫相关判断一律寄坤处理。",
    ])
    assert rewritten[0] == "未提供海外时区，暂按 Asia/Shanghai 计算，请在表单里补齐时区。"
    assert rewritten[1] == "本规则集中宫相关判断一律寄坤处理。"


def test_interpret_user_embeds_chart_and_instruction(monkeypatch) -> None:
    from qimen import service as qimen_service
    from qimen.prompts import INTERPRET_STREAM

    captured: dict = {}

    async def fake_completion(**kwargs) -> AsyncIterator[tuple[str, str]]:
        captured["system"] = kwargs["system"]
        captured["user"] = kwargs["user"]
        yield ("delta", "x")

    class _Config:
        daily_limit = 100

    monkeypatch.setattr(qimen_service, "_provider", lambda: _Config())
    monkeypatch.setattr(qimen_service, "reserve_daily_budget", lambda *_: None)
    monkeypatch.setattr(qimen_service, "stream_completion", fake_completion)
    request = QimenInterpretRequest.model_validate({"chart": _client().post("/v1/qimen/chart", json=CHART_BODY).json()})
    _collect_events(request)
    assert "《奇门默认规则》" in captured["system"]
    assert "《取用神顺序》" in captured["system"]
    assert INTERPRET_STREAM in captured["user"]
    assert "阳遁" in captured["user"]
    assert "能不能动，什么时候动更稳" in captured["user"]
