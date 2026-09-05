"""provider 529 过载退避重试的回归（2026-09-04 生产事故：MiniMax 529 尖峰全链 502）。"""

from __future__ import annotations

import asyncio
import itertools
import json

import httpx
import pytest

import ai_explainer
from ai_explainer import AiFact, AiProviderError


class FakeConfig:
    model = "mock-model"
    api_key = "k" * 8
    base_url = "https://provider.example/v1"
    timeout_seconds = 5.0
    response_format = "json_schema"
    context_secret = b"s" * 32
    daily_limit = 10
    budget_scope = "single_worker"


_OK_BODY = {
    "choices": [{
        "finish_reason": "stop",
        "message": {"content": json.dumps({
            "summary": {"text": "ok", "fact_ids": []},
            "actions": [],
            "caveats": [],
        })},
    }],
    "usage": {},
}


def _install(monkeypatch, statuses: list[int]) -> dict:
    state = {"calls": 0}
    cycle = itertools.cycle(statuses) if len(set(statuses)) == 1 and len(statuses) > 1 else iter(statuses + [statuses[-1]] * 50)

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(cycle)
        state["calls"] += 1
        if status == 200:
            return httpx.Response(200, json=_OK_BODY)
        return httpx.Response(status, json={"error": "overloaded"})

    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs.pop("trust_env", None)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)
    monkeypatch.setattr(ai_explainer, "_PROVIDER_RETRY_BASE_SECONDS", 0.0)
    return state


def _run_complete_once(monkeypatch, statuses: list[int]):
    state = _install(monkeypatch, statuses)

    async def run():
        async with httpx.AsyncClient() as client:
            return await ai_explainer._complete_once(
                client, "问", [AiFact(id="f1", text="事实")],
                FakeConfig(), {"ziwei.chart"}, {}, None, None,
            )

    answer = asyncio.run(run())
    return answer, state


def test_529_then_200_recovers(monkeypatch):
    answer, state = _run_complete_once(monkeypatch, [529, 200])
    assert answer.summary.text == "ok"
    assert state["calls"] == 2, "首次 529 后应重试一次"


def test_persistent_529_raises_provider_error(monkeypatch):
    with pytest.raises(AiProviderError) as excinfo:
        _run_complete_once(monkeypatch, [529, 529, 529, 529])
    assert "529" in str(excinfo.value)
