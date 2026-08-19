import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import app as api_module
from dreams.models import InterpretResponse, SourceOut
from dreams.overlay import overlay_facts


def test_overlay_facts_only_day_and_current_limit() -> None:
    facts = overlay_facts(
        day_pillar="甲子",
        decadal_name="财帛",
        decadal_range=(26, 35),
        yearly_pillar="乙丑",
    )
    texts = [fact.text for fact in facts]
    assert any("流日" in text and "甲子" in text for text in texts)
    assert any("大限" in text and "财帛" in text for text in texts)
    assert any("流年" in text and "乙丑" in text for text in texts)
    assert len(facts) <= 3
    assert all("八字日主" not in text for text in texts)


def _fake_response() -> InterpretResponse:
    return InterpretResponse(essay="主断", sources=[], overlay=None, referral=None)


def test_interpret_schema_essay_and_sources(monkeypatch) -> None:
    async def fake(_request):
        return InterpretResponse(
            essay="一篇文",
            sources=[SourceOut(work="周公解梦", quote="蛇入怀中生贵子", channel="字面")],
            overlay=None,
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


def test_interpret_without_chart(monkeypatch) -> None:
    async def fake(_request):
        return _fake_response()

    monkeypatch.setattr(api_module, "interpret_dream_request", fake)
    client = TestClient(api_module.app)
    res = client.post("/v1/dreams/interpret", json={"dream": "梦见数楼梯台阶"})
    assert res.status_code == 200
    body = res.json()
    assert body["overlay"] is None
    assert "八字" not in res.text


def test_overlay_false_ignores_tokens(monkeypatch) -> None:
    async def fake(request):
        assert request.overlay is False
        return _fake_response()

    monkeypatch.setattr(api_module, "interpret_dream_request", fake)
    client = TestClient(api_module.app)
    res = client.post("/v1/dreams/interpret", json={
        "dream": "梦见数楼梯台阶",
        "overlay": False,
        "context_tokens": ["not-a-real-token"],
    })
    assert res.status_code == 200
    assert res.json()["overlay"] is None
