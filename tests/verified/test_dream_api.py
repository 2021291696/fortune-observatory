import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import app as api_module
from dreams.models import InterpretResponse, SourceOut


def _fake_response() -> InterpretResponse:
    return InterpretResponse(essay="主断", sources=[], referral=None)


def test_interpret_schema_essay_and_sources(monkeypatch) -> None:
    async def fake(_request):
        return InterpretResponse(
            essay="一篇文",
            sources=[SourceOut(work="荣格象征词典", quote="教室象征学习与成长", channel="字面")],
            referral=None,
        )

    monkeypatch.setattr(api_module, "interpret_dream_request", fake)
    client = TestClient(api_module.app)
    res = client.post("/v1/dreams/interpret", json={"dream": "梦见数楼梯台阶"})
    assert res.status_code == 200
    body = res.json()
    assert body["essay"] == "一篇文"
    assert body["sources"][0]["channel"] == "字面"
    assert "scene" not in body
    assert "verdict" not in body
    assert "c3" not in body
    assert "fortune" not in body
    assert "citations" not in body
    assert "associations" not in body
    assert "overlay" not in body


def test_interpret_without_chart(monkeypatch) -> None:
    async def fake(_request):
        return _fake_response()

    monkeypatch.setattr(api_module, "interpret_dream_request", fake)
    client = TestClient(api_module.app)
    res = client.post("/v1/dreams/interpret", json={"dream": "梦见数楼梯台阶"})
    assert res.status_code == 200
    assert "八字" not in res.text


def test_extra_fields_are_rejected(monkeypatch) -> None:
    """对照命盘已下线：overlay/context_tokens 不再是合法字段。"""
    client = TestClient(api_module.app)
    res = client.post("/v1/dreams/interpret", json={
        "dream": "梦见数楼梯台阶",
        "overlay": False,
        "context_tokens": ["not-a-real-token"],
    })
    assert res.status_code == 422
