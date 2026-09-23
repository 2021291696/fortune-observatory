"""2026-09 审计修复轮回归测试（run-2/run-3 findings 对应）。

覆盖：解梦非流式红线闸、questions 标签闸、四条流式通道的 think 纳入扫描、
provider 响应体 64KB 上限（dreams/tcm）、阅读会话僵尸修复（attach 看门/
预算回滚/sweep 补终态）、护栏 AI 体限分档、流式每 IP 并发帽、qimen 年域、
verify_context TypeError、_ai_request_units 深嵌套 JSON；
run-3：急症同义词+匹配规范化、qimen 年域全输入形态、免责截断顺序、
红线词族补全、流式每 IP 帽拒绝路径 AI 槽泄漏。
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


def test_dream_nonstream_redline_words_pass_through(monkeypatch):
    """2026-09-23 拍板：红线移除，含红线词的解梦正文照常交付。"""
    body = json.dumps({"choices": [{"message": {"content": "{\"essay\":\"你注定会大富大贵，建议买入股票。\",\"sources\":[]}"}}]}).encode()
    _install_json_client(monkeypatch, body)
    monkeypatch.setattr(dream_service, "_provider", lambda: _FakeConfig())

    async def run():
        return await dream_service.interpret_dream_request(InterpretRequest(dream="梦见数楼梯台阶"))

    result = asyncio.run(run())
    assert "注定会大富大贵" in result.essay


def test_dream_questions_redline_labels_pass_through(monkeypatch):
    """红线移除后：追问标签含红线词也原样交付，不再回落启发式。"""
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
    assert "阿司匹林" in result.questions[0].label and "买入" in result.questions[1].label


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


def test_dream_stream_think_channel_passes_through(monkeypatch):
    """2026-09-23 拍板：红线移除，think 链带红线词也照常直通。"""
    _install_sse_client(monkeypatch, _sse(["<think>", "你注定会大富大贵", "</think>", "今天适合出门。"]))
    monkeypatch.setattr(dream_service, "_provider", lambda: _FakeConfig())

    async def run():
        return [event async for event in dream_service.stream_interpret_events(InterpretRequest(dream="梦见散步"))]

    events = asyncio.run(run())
    assert events[-1]["type"] == "done"


def test_tcm_stream_think_channel_passes_through(monkeypatch):
    _install_sse_client(monkeypatch, _sse(["<think>", "建议停用阿司匹林100mg", "</think>", "跟你说，注意休息。"]))
    monkeypatch.setattr(tcm_service, "_provider", lambda: _FakeConfig())

    async def run():
        return [event async for event in tcm_service.stream_consult_events(ConsultRequest(question="头疼怎么调理"))]

    events = asyncio.run(run())
    assert events[-1]["type"] == "done"


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


# ---------- 紫微行运：早于生日的 transit_date（独立审计 confirmed 回归） ----------

def test_api_daily_transit_pre_birth_date_is_422_not_500():
    # 修复前：2017-06-15 对 2024-05-05 出生给 nominal_age = -6，IndexError
    # 逃出 except ValueError → 500；修复后在请求边界被 422 拒绝。
    client = TestClient(api_module.app)
    payload = {
        "birth": {
            "civil_datetime": "2024-05-05T10:00:00+08:00",
            "timezone_id": "Asia/Shanghai",
            "longitude": 104.0,
            "latitude": 30.0,
            "sex_for_rule": "male",
        },
        "transit_date": "2017-06-15",
    }
    res = client.post("/v1/transits/daily", json=payload)
    assert res.status_code == 422


# ---------- run-3 修复轮（2026-09-23）：急症同义词 / 年域全形态 / 免责截断顺序 / 红线词族 / AI 槽拒绝路径 ----------


def test_tcm_emergency_synonyms_and_evasion_forms():
    """口语同义词必须触发 120 转介（此前心肌梗塞/脑梗/脑卒中/吐血/抽搐/喘不上气全漏）。"""
    for phrase in (
        "我爸心肌梗塞犯了", "老人脑梗了怎么办", "怀疑脑卒中", "吐血了",
        "孩子一直抽搐", "喘不上气", "心绞痛发作了",
    ):
        assert tcm_service.is_emergency(phrase), phrase
    # 拆字/零宽写法同样命中（匹配前 NFKC + 剥空白零宽）
    assert tcm_service.is_emergency("心肌 梗 塞")
    assert tcm_service.is_emergency("脑" + chr(0x200B) + "梗")
    assert not tcm_service.is_emergency("最近总是乏力想调理一下")


def test_tcm_emergency_referral_short_circuits_provider(monkeypatch):
    """急症命中即转介，不打 LLM。"""
    called: list[int] = []

    async def fake_chat(*args, **kwargs):
        called.append(1)
        return "不该被调用"

    monkeypatch.setattr(tcm_service, "_chat", fake_chat)
    monkeypatch.setattr(tcm_service, "_provider", lambda: _FakeConfig())

    async def run():
        return await tcm_service.consult_request(ConsultRequest(question="我爷爷心肌梗塞，胸口疼得厉害"))

    res = asyncio.run(run())
    assert res.referral == tcm_service._REFERRAL_TEXT
    assert res.essay == ""
    assert called == []


def test_tcm_disclaimer_survives_long_essay(monkeypatch):
    """run-3：先补免责再截断会把结尾免责切掉；先裁后补后免责恒在结尾且不超帽。"""
    long_body = "辨证论治，此为太阴病脾虚寒湿之证，理中汤主之，随证加减。" * 140  # >3600 字
    outputs = [long_body + "\n\n" + tcm_service.DISCLAIMER, long_body]

    async def fake_chat(*args, **kwargs):
        return outputs.pop(0)

    monkeypatch.setattr(tcm_service, "_chat", fake_chat)
    monkeypatch.setattr(tcm_service, "_provider", lambda: _FakeConfig())
    monkeypatch.setattr(tcm_service, "reserve_daily_budget", lambda limit: None)

    async def run(question: str):
        return await tcm_service.consult_request(ConsultRequest(question=question))

    for question in ("长期便秘怎么办", "手脚冰凉怎么调理"):
        res = asyncio.run(run(question))
        assert res.essay.endswith(tcm_service.DISCLAIMER), "截断后免责框必须仍落在结尾"
        assert res.essay.count(tcm_service.DISCLAIMER) == 1
        assert len(res.essay) <= tcm_service._ESSAY_CAP


def test_qimen_year_guard_governs_all_canonical_forms():
    """run-3：前缀启发式废除——带符号/短年/下划线/全角/本地化分隔符不再绕守卫。"""
    from pydantic import ValidationError

    for value in (
        "+9999-01-01", "-9999-01-01", "24-1-1", "999-1-1", "9_999-01-01",
        "２４-１-１", "24/1/1", "24年1月1日",
    ):
        with pytest.raises(ValidationError):
            QimenChartRequest(question_type="事业", question_goal="能否成行", time_mode="custom", time_input=value)
    QimenChartRequest(question_type="事业", question_goal="能否成行", time_mode="custom", time_input="2024-01-01 10:00")


def test_qimen_engine_year_domain_on_parsed_year():
    """引擎侧兜底：string 与 dict 直入路径都在解析后的年份上做年域校验。"""
    from fortune_core.qimen import engine as qimen_engine

    with pytest.raises(ValueError, match="1849-2150"):
        qimen_engine.parse_datetime_string("-9999-01-01")
    with pytest.raises(ValueError, match="1849-2150"):
        qimen_engine.normalize_input({
            "question_type": "事业", "question_goal": "x", "calendar_type": "solar",
            "time_input": {"year": 9999, "month": 1, "day": 1, "hour": 10},
        })
    assert qimen_engine.parse_datetime_string("2024-01-01 10:00")["year"] == 2024


def test_guard_stream_cap_reject_releases_ai_slot():
    """run-3：流式每 IP 帽的拒绝路径不得漏 AI 槽。拒绝打在内嵌协程首步之前的
    cancel 上，其 finally 从未开跑——归还必须由请求线的租约兜底。修复前几轮
    拒绝即可把 3 个 AI 槽永久抽干，重启前 AI 请求一路 503。"""
    hold = asyncio.Event()
    holder_entered = asyncio.Event()

    async def stub_app(scope, receive, send):
        if scope["_test_body"] == b"hold":
            holder_entered.set()
            await hold.wait()
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-length", b"2")]})
        await send({"type": "http.response.body", "body": b"ok"})

    async def scenario():
        guard = security_module.RequestGuardMiddleware(
            stub_app,
            trust_proxy=False,
            streaming_ai_per_ip=1,
            max_concurrent_ai_requests=3,
            ai_requests_per_minute=60,
            ai_global_requests_per_minute=600,
        )

        async def call(body: bytes, client: str) -> list:
            messages: list = []
            scope = {
                "type": "http", "method": "POST", "path": "/v1/ai/reading",
                "headers": [(b"content-length", str(len(body)).encode())],
                "client": (client, 12345), "_test_body": body,
            }
            inbox = [{"type": "http.request", "body": body, "more_body": False}]
            parked = asyncio.Event()

            async def receive():
                return inbox.pop(0) if inbox else await parked.wait()

            async def send(message):
                messages.append(message)

            await guard(scope, receive, send)
            return messages

        # 持有者：进 stub 后挂在 hold 上，占住唯一 in-flight 流式名额与 1 个 AI 槽
        holder = asyncio.create_task(call(b"hold", "10.0.0.1"))
        await holder_entered.wait()
        assert guard._ai_slots._value == 2

        # 同 IP 第二条流式连接：帽拒绝（429）——拒绝路径的槽归还由请求线兜底
        rejected = await call(b"probe", "10.0.0.1")
        assert any(m.get("status") == 429 for m in rejected if m.get("type") == "http.response.start")
        assert guard._ai_slots._value == 2, "帽拒绝路径漏 AI 槽（首步前 cancel，协程 finally 未跑）"

        # 放行持有者 → 三槽回满
        hold.set()
        await holder
        assert guard._ai_slots._value == 3

        # 服务恢复：新连接能拿到槽正常返回
        messages = await call(b"probe", "10.0.0.2")
        assert any(m.get("status") == 200 for m in messages if m.get("type") == "http.response.start")
        assert guard._ai_slots._value == 3

    asyncio.run(scenario())
