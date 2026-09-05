"""解梦流式的协议级回归：不经路由 mock，直接以假 SSE 流驱动 stream_interpret_events。

背景：491e8a0 曾把 stream_completion 改为 (kind, text) 元组而 dreams 侧没跟上，
解梦流式全坏且 e2e mock 掉路由未拦住（2026-09-04 修复）。本文件防止回归。
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import dreams.service as dream_service
from ai_explainer import AiBudgetExceeded
from dreams.models import InterpretRequest


class FakeConfig:
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


def test_dream_stream_events_are_strings(monkeypatch):
    body = _sse([
        "<think>", "组织荣格口径", "</think>",
        "梦见蛇，", "《梦的解析》里说：「梦是通往潜意识的无声小径」。",
    ])
    _install_sse_client(monkeypatch, body)
    monkeypatch.setattr(dream_service, "_provider", lambda: FakeConfig())
    charged: list[int] = []
    monkeypatch.setattr(dream_service, "reserve_daily_budget", lambda limit: charged.append(limit))

    async def run():
        request = InterpretRequest(dream="梦见大蛇盘在门口")
        return [event async for event in dream_service.stream_interpret_events(request)]

    events = asyncio.run(run())
    kinds = [event["type"] for event in events]
    assert kinds == ["think", "delta", "delta", "done"], kinds
    for event in events:
        assert isinstance(event.get("text", ""), str)
    text = "".join(event["text"] for event in events if event["type"] == "delta")
    assert text.startswith("梦见蛇")
    assert events[-1]["sources"], "done 事件应携带从正文提取的口径来源"
    assert charged == [FakeConfig.daily_limit], "解梦流式必须接日预算闸"


def test_dream_stream_budget_exceeded_propagates(monkeypatch):
    _install_sse_client(monkeypatch, _sse(["x"]))
    monkeypatch.setattr(dream_service, "_provider", lambda: FakeConfig())

    def boom(limit):
        raise AiBudgetExceeded("AI daily request budget exhausted")

    monkeypatch.setattr(dream_service, "reserve_daily_budget", boom)

    async def run():
        request = InterpretRequest(dream="梦见大蛇盘在门口")
        async for _ in dream_service.stream_interpret_events(request):
            pass

    with pytest.raises(AiBudgetExceeded):
        asyncio.run(run())
