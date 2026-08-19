import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from ai_explainer import AiConfigurationError, AiProviderError
from dreams.models import InterpretResponse, SourceOut
from dreams.service import write_essay


def _result(**kwargs) -> InterpretResponse:
    base = dict(essay="", sources=[], overlay=None, referral=None)
    base.update(kwargs)
    return InterpretResponse(**base)


def test_referral_skips_model(monkeypatch) -> None:
    async def boom(*_a, **_k):
        raise AssertionError("must not call chat")
    monkeypatch.setattr("dreams.service._chat", boom)
    out = asyncio.run(write_essay("反复噩梦", _result(referral="转介"), None))
    assert out.essay == ""
    assert out.referral == "转介"


def test_missing_provider_raises(monkeypatch) -> None:
    monkeypatch.setattr("dreams.service._provider", lambda: None)
    with pytest.raises(AiConfigurationError):
        asyncio.run(write_essay("梦见蛇", _result(), None))


def test_empty_model_text_raises(monkeypatch) -> None:
    monkeypatch.setattr("dreams.service._provider", lambda: object())

    async def empty(_sys, _user):
        return "   "
    monkeypatch.setattr("dreams.service._chat", empty)
    with pytest.raises(AiProviderError):
        asyncio.run(write_essay("梦见蛇", _result(), None))


def test_chat_ok_sets_essay(monkeypatch) -> None:
    monkeypatch.setattr("dreams.service._provider", lambda: object())

    async def ok(_sys, _user):
        assert "梦见蛇" in _user
        assert "蛇入怀" in _user
        assert "字面" in _user
        return "这是一篇很长的解梦正文。"
    monkeypatch.setattr("dreams.service._chat", ok)
    out = asyncio.run(write_essay(
        "梦见蛇",
        _result(sources=[SourceOut(work="周公解梦", quote="蛇入怀中生贵子", channel="字面")]),
        "流日甲子",
    ))
    assert out.essay == "这是一篇很长的解梦正文。"


from fastapi import HTTPException
from dreams.service import interpret_dream_request
from dreams.models import InterpretRequest


def test_embed_fail_still_retrieves(monkeypatch) -> None:
    from dreams.embed import EmbedError
    from dreams.index import MemoryIndex
    from dreams.models import CorpusRecord, Layer, Polar

    rec = CorpusRecord(
        id="s", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="蛇入怀中生贵子", citation_eligible=False, polarity=Polar.none,
    )
    idx = MemoryIndex([rec], [[1.0, 0.0]])
    monkeypatch.setattr("dreams.service.get_index", lambda: idx)
    monkeypatch.setattr("dreams.service.embed_texts", lambda *_a, **_k: (_ for _ in ()).throw(EmbedError("down")))

    async def fake_essay(dream, result, overlay):
        return result.model_copy(update={"essay": "ok"})
    monkeypatch.setattr("dreams.service.write_essay", fake_essay)
    monkeypatch.setattr("dreams.service._provider", lambda: None)

    out = __import__("asyncio").run(
        interpret_dream_request(InterpretRequest(dream="梦见蛇入怀里"))
    )
    assert any("入怀" in s.quote or "贵子" in s.quote for s in out.sources)
    assert out.essay == "ok"


def test_bad_overlay_token_is_422(monkeypatch) -> None:
    class Cfg:
        context_secret = "x" * 32

    monkeypatch.setattr("dreams.service._provider", lambda: Cfg())

    def boom(*_a, **_k):
        raise ValueError("bad token")
    monkeypatch.setattr("dreams.service._verified_facts", boom)

    with pytest.raises(HTTPException) as caught:
        __import__("asyncio").run(
            interpret_dream_request(
                InterpretRequest(dream="梦见蛇入怀里", overlay=True, context_tokens=["nope"])
            )
        )
    assert caught.value.status_code == 422
