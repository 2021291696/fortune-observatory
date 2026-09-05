"""流式内容安全对齐的回归：reading/解梦收尾全文校验与非流式共用 safety_violation。

背景（2026-09-05 审查）：非流式 _parse_answer 有确定性断语/用药/投资三道红线，
流式路径此前原样转发模型输出，双标。本文件钉住：流式收尾必须校验、
命中必须以 error（detail 带 safety violation）收尾且不落 done。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import dreams.service as dream_service
import reading_agent
from ai_explainer import safety_violation
from dreams.models import InterpretRequest
from reading_agent import StreamSession


def test_safety_violation_categories():
    assert safety_violation("你注定会大富大贵") == "deterministic"
    assert safety_violation("建议服用阿司匹林缓解") == "medical"
    assert safety_violation("DEMENTIA 阿司匹林") == "medical"  # medical 大小写不敏感
    assert safety_violation("可以考虑买入股票") == "investment"
    assert safety_violation("适合主动沟通、修复关系，把话说开。") is None


def test_reading_stream_safety_violation_ends_with_error(monkeypatch):
    async def fake_stream(**_kwargs):
        yield ("think", "组织口径")
        yield ("delta", "你注定")
        yield ("delta", "会大富大贵。")

    monkeypatch.setattr(reading_agent, "stream_reading", fake_stream)

    async def run():
        session = StreamSession("test:safety")
        await reading_agent.generate_into_session(session, question="q", facts=[], bundle_types=set())
        return session

    session = asyncio.run(run())
    assert session.status == "error"
    assert session.error_detail is not None and "safety violation" in session.error_detail
    kinds = [kind for kind, _ in session.events]
    assert "done" not in kinds
    assert kinds[-1] == "error"


def test_reading_stream_clean_text_ends_with_done(monkeypatch):
    async def fake_stream(**_kwargs):
        yield ("delta", "适合主动沟通，把话说开。")

    monkeypatch.setattr(reading_agent, "stream_reading", fake_stream)

    async def run():
        session = StreamSession("test:clean")
        await reading_agent.generate_into_session(session, question="q", facts=[], bundle_types=set())
        return session

    session = asyncio.run(run())
    assert session.status == "done"
    assert session.events[-1][0] == "done"


def test_finish_is_atomic_for_late_attacher(monkeypatch):
    """status 变更与终态事件入列必须同锁：finish 后 attach 的订阅者
    回放里必须直接看到终态事件，而不是挂到 ping 超时。"""
    async def run():
        session = StreamSession("test:atomic")
        await session.finish("done")
        collected = []
        async for event in session.attach():
            collected.append(event)
            break  # 非 live 会话：回放完终态后由 ping 超时路径返回，取首个即可
        return session, collected

    session, collected = asyncio.run(run())
    assert session.status == "done"
    assert collected and collected[0][0] == "done"


class _FakeConfig:
    model = "mock-model"
    api_key = "k" * 8
    base_url = "https://provider.example/v1"
    timeout_seconds = 5.0
    response_format = "json_schema"
    context_secret = b"s" * 32
    daily_limit = 10
    budget_scope = "single_worker"


def _sse(chunks: list[str]) -> bytes:
    frames = [
        b"data: " + json.dumps({"choices": [{"delta": {"content": c}, "finish_reason": None}]}).encode()
        + b"\n\n"
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


def test_dream_stream_safety_violation(monkeypatch):
    body = _sse(["这段说明白，先", "去买股票加仓，稳赚。"])
    _install_sse_client(monkeypatch, body)
    monkeypatch.setattr(dream_service, "_provider", lambda: _FakeConfig())
    monkeypatch.setattr(dream_service, "reserve_daily_budget", lambda limit: None)

    async def run():
        request = InterpretRequest(dream="梦见大蛇盘在门口")
        return [event async for event in dream_service.stream_interpret_events(request)]

    events = asyncio.run(run())
    kinds = [event["type"] for event in events]
    assert "done" not in kinds, "红线命中不得落 done（否则前端会当正常结果保存）"
    assert kinds[-1] == "error"
    assert events[-1]["code"] == "safety"
    assert "safety violation" in events[-1]["detail"]
