"""流式内容直通回归：reading/解梦不做输出红线拦截（2026-09-23 拍板）。

背景：平台自用，确定性断语/用药/投资三族红线于 2026-09-23 整体移除
（此前命中即整篇丢弃，已计费内容白扔）。本文件钉住新契约：
红线词原样通过、正常落 done；自伤/急症转介（另一条人身安全路由）不受影响。
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
from dreams.models import InterpretRequest
from reading_agent import StreamSession


def test_reading_stream_redline_words_pass_through(monkeypatch):
    """红线词（注定/一定会）不再拦截：正文照常落 done。"""
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
    assert session.status == "done"
    body = "".join(text for kind, text in session.events if kind == "delta")
    assert "注定" in body and "大富大贵" in body
    assert session.events[-1][0] == "done"


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


def test_dream_stream_redline_words_pass_through(monkeypatch):
    body = _sse(["这段说明白，先", "去买股票加仓，稳赚。"])
    _install_sse_client(monkeypatch, body)
    monkeypatch.setattr(dream_service, "_provider", lambda: _FakeConfig())
    monkeypatch.setattr(dream_service, "reserve_daily_budget", lambda limit: None)

    async def run():
        request = InterpretRequest(dream="梦见大蛇盘在门口")
        return [event async for event in dream_service.stream_interpret_events(request)]

    events = asyncio.run(run())
    kinds = [event["type"] for event in events]
    assert kinds[-1] == "done"
    body_text = "".join(event["text"] for event in events if event["type"] == "delta")
    assert "股票加仓" in body_text
