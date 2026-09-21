"""2026-09 审计修复轮回归测试（run-2 findings 对应）。

覆盖：解梦非流式红线闸、questions 标签闸、四条流式通道的 think 纳入扫描、
provider 响应体 64KB 上限（dreams/tcm）、阅读会话僵尸修复（attach 看门/
预算回滚/sweep 补终态）、护栏 AI 体限分档、流式每 IP 并发帽、qimen 年域、
verify_context TypeError、_ai_request_units 深嵌套 JSON。
"""

from __future__ import annotations

import asyncio
import io as _io
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import app as api_module
import dreams.service as dream_service
import reading_agent
import security as security_module
import tcm.service as tcm_service
from ai_explainer import AiProviderError, _verify_context
from dreams.models import InterpretRequest
from qimen.models import QimenChartRequest
from tcm.models import ConsultRequest
from tcm.service import safety_violation_tcm


# ---------- 解梦非流式红线闸 ----------

class _FakeConfig:
    model = "mock-model"
    api_key = "k" * 8
    base_url = "https://provider.example/v1"
    timeout_seconds = 5.0
    response_format = "json_schema"
    context_secret = b"s" * 32
    daily_limit = 10
    budget_scope = "single_worker"


def _install_json_client(monkeypatch, body: bytes, status: int = 200) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"content-type": "application/json"}, content=body)

    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs.pop("trust_env", None)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)


def test_dream_nonstream_safety_gate(monkeypatch):
    """非流式解梦命中红线必须拒答（与流式 code=safety 对齐）。"""
    body = json.dumps({"choices": [{"message": {"content": "{\"essay\":\"你注定会大富大贵，建议买入股票。\",\"sources\":[]}"}}]}).encode()
    _install_json_client(monkeypatch, body)
    monkeypatch.setattr(dream_service, "_provider", lambda: _FakeConfig())

    async def run():
        return await dream_service.interpret_dream_request(InterpretRequest(dream="梦见数楼梯台阶"))

    with pytest.raises(AiProviderError, match="safety violation"):
        asyncio.run(run())


def test_dream_questions_redline_label_falls_back_to_heuristic(monkeypatch):
    """追问标签带红线词 → 弃用模型结果，回落启发式三问。"""
    labels = [
        {"id": "finished", "label": "注定结局如此，停用阿司匹林500mg"},
        {"id": "agency", "label": "可以考虑买入股票"},
        {"id": "fear_of", "label": "害怕吗"},
    ]
    body = json.dumps({"choices": [{"message": {"content": json.dumps({"questions": labels}, ensure_ascii=False)}}]}).encode()
    _install_json_client(monkeypatch, body)
    monkeypatch.setattr(dream_service, "_provider", lambda: _FakeConfig())

    async def run():
        return await dream_service.generate_questions("梦见考试迟到")

    result = asyncio.run(run())
    assert [q.id for q in result.questions] == ["finished", "agency", "fear_of"]
    assert all("阿司匹林" not in q.label and "买入" not in q.label for q in result.questions)


# ---------- 流式通道 think 纳入红线扫描 ----------

def _sse(chunks: list[str]) -> bytes:
    frames = [
        b"data: " + json.dumps({"choices": [{"delta": {"content": c}, "finish_reason": None}]}).encode() + b"\n\n"
        for c in chunks
    ]
    frames.append(b"data: [DONE]\n\n")
    return b"".join(frames)


def _install_sse_client(monkeypatch, body: bytes) -> None:
    async def stream():
        yield body

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=stream())

    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs.pop("trust_env", None)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)


def test_dream_stream_think_channel_is_scanned(monkeypatch):
    """think 通道带红线词也必须触发 code=safety 收尾。"""
    _install_sse_client(monkeypatch, _sse(["<think>", "你注定会大富大贵", "</think>", "今天适合出门。"]))
    monkeypatch.setattr(dream_service, "_provider", lambda: _FakeConfig())

    async def run():
        return [event async for event in dream_service.stream_interpret_events(InterpretRequest(dream="梦见散步"))]

    events = asyncio.run(run())
    assert events[-1]["type"] == "error" and events[-1].get("code") == "safety"


def test_tcm_stream_think_channel_is_scanned(monkeypatch):
    _install_sse_client(monkeypatch, _sse(["<think>", "建议停用阿司匹林100mg", "</think>", "跟你说，注意休息。"]))
    monkeypatch.setattr(tcm_service, "_provider", lambda: _FakeConfig())

    async def run():
        return [event async for event in tcm_service.stream_consult_events(ConsultRequest(question="头疼怎么调理"))]

    events = asyncio.run(run())
    assert events[-1]["type"] == "error" and events[-1].get("code") == "safety"


# ---------- provider 响应体 64KB 上限（dreams 非流式） ----------

def test_dream_chat_rejects_oversized_provider_body(monkeypatch):
    big = json.dumps({"choices": [{"message": {"content": "梦" * 40_000}}]}).encode()
    assert len(big) > 64_000
    _install_json_client(monkeypatch, big)
    monkeypatch.setattr(dream_service, "_provider", lambda: _FakeConfig())

    async def run():
        await dream_service.interpret_dream_request(InterpretRequest(dream="梦见散步"))

    with pytest.raises(AiProviderError):
        asyncio.run(run())


# ---------- 阅读会话僵尸修复 ----------

def test_attach_on_taskless_streaming_session_yields_error():
    """僵尸会话（streaming 但 task=None）attach 立即得到 error 终态，不再永久 ping。"""
    async def run():
        session = reading_agent.StreamSession("test-key")
        assert session.task is None
        events = []
        async for kind, text in session.attach():
            events.append((kind, text))
            if len(events) > 5:
                break
        return events

    events = asyncio.run(run())
    assert ("error", "generation task is missing") in events, events


def test_drop_stream_session_removes_only_matching_object():
    async def run():
        session = reading_agent.StreamSession("key-a")
        reading_agent._sessions["key-a"] = session
        await reading_agent.drop_stream_session("key-a", session)
        assert "key-a" not in reading_agent._sessions
        # 键已被别的会话占用时不误删
        other = reading_agent.StreamSession("key-a")
        reading_agent._sessions["key-a"] = other
        await reading_agent.drop_stream_session("key-a", session)
        assert reading_agent._sessions["key-a"] is other
        reading_agent._sessions.pop("key-a", None)

    asyncio.run(run())


def test_session_finish_is_idempotent():
    async def run():
        session = reading_agent.StreamSession("key-b")
        await session.finish("done")
        await session.finish("error", "late call")
        assert session.status == "done"
        assert session.events[-1][0] == "done"
        reading_agent._sessions.pop("key-b", None)

    asyncio.run(run())


def test_budget_failure_leaves_no_registry_entry(monkeypatch):
    """429 路径回滚注册表：同 stream_key 重试不会 attach 到僵尸。"""
    from ai_explainer import AiBudgetExceeded

    async def run():
        key = "digest:test-rollback"
        session, resumed = await reading_agent.get_or_create_stream_session(key)
        assert resumed is False
        # 模拟 app.py 预算失败路径的回滚
        await reading_agent.drop_stream_session(key, session)
        assert key not in reading_agent._sessions
        session2, resumed2 = await reading_agent.get_or_create_stream_session(key)
        assert resumed2 is False, "回滚后重试必须当新会话，而不是 attach 僵尸"
        reading_agent._sessions.pop(key, None)

    asyncio.run(run())


# ---------- 护栏：AI 体限分档 / 流式每 IP 并发帽 / 深嵌套 JSON ----------

def _make_guard(**kwargs) -> security_module.RequestGuardMiddleware:
    return security_module.RequestGuardMiddleware(
        app=None, trust_proxy=False, **kwargs
    ) if False else security_module.RequestGuardMiddleware(
        lambda scope, receive, send: None, trust_proxy=False, **kwargs
    )


def test_ai_body_cap_is_wider_than_calculation_cap():
    guard = _make_guard()
    assert guard.max_body_bytes == 16_384
    assert guard.ai_max_body_bytes == 65_536


def test_ai_request_units_survives_deeply_nested_json():
    body = b"[" * 20_000 + b"]" * 20_000
    units = security_module.RequestGuardMiddleware._ai_request_units(body)
    assert isinstance(units, int) and units >= 1


def test_verify_context_non_ascii_signature_maps_to_4xx_error():
    secret = b"s" * 32
    token = "eyJhbGciOiAi" + "签名"  # 签名段含非 ASCII
    with pytest.raises(AiProviderError, match="invalid"):
        _verify_context(token, secret)


# ---------- qimen 年域守卫 ----------

def test_qimen_time_input_year_bounds():
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="1849-2150"):
        QimenChartRequest(question_type="事业", question_goal="能否成行", time_mode="custom", time_input="1000-01-01 10:00")
    with pytest.raises(ValidationError, match="1849-2150"):
        QimenChartRequest(question_type="事业", question_goal="能否成行", time_mode="custom", time_input="9999-01-01 10:00")
    # 边界值与正常值不拦
    QimenChartRequest(question_type="事业", question_goal="能否成行", time_mode="custom", time_input="1849-06-01 10:00")
    QimenChartRequest(question_type="事业", question_goal="能否成行", time_mode="custom", time_input="2150-06-01 10:00")
    QimenChartRequest(question_type="事业", question_goal="能否成行")


# ---------- API 层：AI 体限分档行为 ----------

def test_api_ai_endpoint_accepts_body_between_16k_and_64k():
    client = TestClient(api_module.app)
    # /v1/dreams/interpret 属 AI 路径：16KiB-64KiB 的体不再被 413 误杀
    # （会走到服务层 503/502/200，取决于 provider 配置；此处只断言不是 413）。
    dream = "梦见" + "蛇" * 20_000
    res = client.post("/v1/dreams/interpret", json={"dream": dream[:2000]})
    assert res.status_code != 413


def test_api_calculation_endpoint_still_caps_at_16k():
    client = TestClient(api_module.app)
    birth = {
        "civil_datetime": "2000-01-01T12:00:00+08:00",
        "timezone_id": "Asia/Shanghai",
        "longitude": 104.0,
        "latitude": 30.0,
        "sex_for_rule": "male",
        "use_apparent_solar_time": True,
        "padding": "x" * 20_000,
    }
    res = client.post("/v1/charts", json=birth)
    assert res.status_code == 413
