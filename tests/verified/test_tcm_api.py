"""中医问诊契约测试（provider 全 mock，零真实配额）。

覆盖域专用安全闸（方剂语言放行/西药与断语拦截）、免责框强校验、
急症确定性转介、流式协议与 API 层行为。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import app as api_module
import tcm.service as tcm_service
from ai_explainer import AiBudgetExceeded
from tcm.models import ConsultRequest
from tcm.service import DISCLAIMER, safety_violation_tcm


# ---------- 域专用安全闸 ----------

def test_formula_language_passes() -> None:
    assert safety_violation_tcm("桂枝(四两) 芍药(三两)，以水七升煮取三升，温服一升，啜热稀粥一升") is None
    assert safety_violation_tcm("**辨证：太阴病（脾虚寒湿·理中汤证）**，人参三钱") is None


def test_western_med_blocked() -> None:
    assert safety_violation_tcm("口服阿司匹林100mg") == "western_med"
    assert safety_violation_tcm("建议输液治疗") == "western_med"
    assert safety_violation_tcm("每天3片") == "western_med"


def test_deterministic_and_investment_blocked() -> None:
    assert safety_violation_tcm("这个病一定会断根") == "deterministic"
    assert safety_violation_tcm("可以买入医药股") == "investment"


def test_herb_doses_in_chinese_units_not_blocked() -> None:
    """中药剂量语言（两/钱/枚/升）不得被阿拉伯数字单位正则误伤。"""
    assert safety_violation_tcm("大枣十二枚，石膏鸡蛋大") is None
    assert safety_violation_tcm("生附子3钱棉布包先煎") is None


# ---------- 免责框强校验 ----------

def test_disclaimer_appended_when_missing() -> None:
    out = tcm_service._enforce_disclaimer("桂枝汤主之，汗一透就没了。")
    assert out.endswith(DISCLAIMER)
    assert out.count(DISCLAIMER) == 1


def test_disclaimer_kept_when_present() -> None:
    essay = f"我跟你说，太阳中风。{DISCLAIMER}"
    assert tcm_service._enforce_disclaimer(essay) == essay


# ---------- 急症转介 ----------

def test_emergency_referral_without_llm(monkeypatch) -> None:
    """急症命中即确定性转介：不打 provider、不扣预算。"""
    charged: list[int] = []
    monkeypatch.setattr(tcm_service, "reserve_daily_budget", lambda limit: charged.append(limit))

    def boom(*_args, **_kwargs):
        raise AssertionError("急症路径不得调用 provider")

    monkeypatch.setattr(tcm_service, "_chat", boom)

    async def run():
        return [event async for event in tcm_service.stream_consult_events(
            ConsultRequest(question="我胸口剧痛出冷汗，喘不上气"))]

    events = asyncio.run(run())
    assert events[0] == {"type": "delta", "text": tcm_service._REFERRAL_TEXT}
    assert events[-1] == {"type": "done", "sources": []}
    assert charged == []


def test_non_emergency_not_referral() -> None:
    assert not tcm_service.is_emergency("长期手脚冰凉怕冷怎么调养")


# ---------- 流式协议 ----------

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


def test_tcm_stream_protocol_and_disclaimer_tail(monkeypatch) -> None:
    body = _sse([
        "<think>", "先辨六经", "</think>",
        "我跟你说，这是太阳中风，", "《伤寒论》第12条讲：「太阳中风，阳浮而阴弱」。",
    ])
    _install_sse_client(monkeypatch, body)
    monkeypatch.setattr(tcm_service, "_provider", lambda: FakeConfig())
    charged: list[int] = []
    monkeypatch.setattr(tcm_service, "reserve_daily_budget", lambda limit: charged.append(limit))

    async def run():
        return [event async for event in tcm_service.stream_consult_events(
            ConsultRequest(question="感冒出汗怕风怎么回事"))]

    events = asyncio.run(run())
    kinds = [event["type"] for event in events]
    assert kinds[0] == "think" and kinds[-1] == "done", kinds
    text = "".join(event["text"] for event in events if event["type"] == "delta")
    assert text.startswith("我跟你说")
    assert DISCLAIMER in text, "免责框缺失时收尾必须补齐"
    assert events[-1]["sources"], "done 事件应携带口径来源"
    assert charged == [FakeConfig.daily_limit]


def test_tcm_stream_safety_close_out(monkeypatch) -> None:
    _install_sse_client(monkeypatch, _sse(["先吃阿司匹林100mg看看。"]))
    monkeypatch.setattr(tcm_service, "_provider", lambda: FakeConfig())

    async def run():
        return [event async for event in tcm_service.stream_consult_events(
            ConsultRequest(question="头疼吃什么药好"))]

    events = asyncio.run(run())
    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "safety"


def test_tcm_stream_budget_exceeded_propagates(monkeypatch) -> None:
    _install_sse_client(monkeypatch, _sse(["x"]))
    monkeypatch.setattr(tcm_service, "_provider", lambda: FakeConfig())

    def boom(limit):
        raise AiBudgetExceeded("AI daily request budget exhausted")

    monkeypatch.setattr(tcm_service, "reserve_daily_budget", boom)

    async def run():
        async for _ in tcm_service.stream_consult_events(ConsultRequest(question="失眠多梦怎么调理")):
            pass

    with pytest.raises(AiBudgetExceeded):
        asyncio.run(run())


# ---------- API 层 ----------

def test_api_consult_schema(monkeypatch) -> None:
    from tcm.models import ConsultResponse

    async def fake(_request):
        return ConsultResponse(essay=f"主断正文。{DISCLAIMER}", sources=[], referral=None)

    monkeypatch.setattr(api_module, "consult_request", fake)
    client = TestClient(api_module.app)
    res = client.post("/v1/tcm/consult", json={"question": "长期便秘怎么办"})
    assert res.status_code == 200
    body = res.json()
    assert body["essay"].endswith(DISCLAIMER)
    assert "referral" in body and "sources" in body


def test_api_consult_referral(monkeypatch) -> None:
    async def fake(_request):
        return tcm_service._emergency_result()

    monkeypatch.setattr(api_module, "consult_request", fake)
    client = TestClient(api_module.app)
    res = client.post("/v1/tcm/consult", json={"question": "我父亲突然昏迷了"})
    assert res.status_code == 200
    assert "120" in res.json()["referral"]


def test_api_consult_validation_rejects_extra_fields() -> None:
    client = TestClient(api_module.app)
    res = client.post("/v1/tcm/consult", json={"question": "梦见大蛇盘在门口", "dream": "多余字段"})
    assert res.status_code == 422


def test_api_consult_stream_sse_shape(monkeypatch) -> None:
    async def fake_events(_request):
        yield {"type": "delta", "text": "我跟你说，太阳中风。"}
        yield {"type": "done", "sources": []}

    monkeypatch.setattr(api_module, "stream_consult_events", fake_events)
    client = TestClient(api_module.app)
    with client.stream("POST", "/v1/tcm/consult/stream", json={"question": "感冒出汗怕风"}) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        body = "".join(chunk for chunk in res.iter_text())
    assert '"type": "delta"' in body and "[DONE]" in body
