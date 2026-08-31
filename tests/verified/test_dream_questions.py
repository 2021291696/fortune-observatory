import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import app as api_module
from dreams.models import ComplexAnswer, InterpretResponse, QuestionsResponse, QuestionOut
from dreams.service import compose_query, heuristic_questions


def test_heuristic_questions_mention_dream() -> None:
    questions = heuristic_questions("我梦见一条蛇钻进怀里然后跑了")
    assert [item.id for item in questions] == ["finished", "agency", "fear_of"]
    assert "蛇" in questions[0].label or "怀里" in questions[0].label


def test_compose_query_appends_answers() -> None:
    query = compose_query("梦见蛇", [ComplexAnswer(id="finished", question="做完了吗", answer="没有")])
    assert "梦见蛇" in query
    assert "做完了吗：没有" in query


def test_compose_query_skips_empty_answers() -> None:
    assert compose_query("梦见蛇", [ComplexAnswer(id="finished", question="做完了吗", answer=None)]) == "梦见蛇"


def test_questions_endpoint_without_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "dreams.service.get_provider_config",
        lambda: None,
    )
    client = TestClient(api_module.app)
    res = client.post("/v1/dreams/questions", json={"dream": "梦见蛇钻进怀里怎么也赶不走"})
    assert res.status_code == 200
    body = QuestionsResponse.model_validate(res.json())
    assert len(body.questions) == 3
    assert all(isinstance(item, QuestionOut) for item in body.questions)


def test_interpret_endpoint_accepts_plain_dream(monkeypatch) -> None:
    async def fake(request):
        assert request.dream == "梦见数楼梯台阶"
        return InterpretResponse(essay="主断", sources=[], referral=None)

    monkeypatch.setattr(api_module, "interpret_dream_request", fake)
    client = TestClient(api_module.app)
    res = client.post("/v1/dreams/interpret", json={"dream": "梦见数楼梯台阶"})
    assert res.status_code == 200
