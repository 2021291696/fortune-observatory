import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from dreams.index import MemoryIndex
from dreams.models import CorpusRecord, InterpretResponse, Layer, Polar, SourceOut
from dreams.pipeline import interpret


def _rec(rid: str, title: str, text: str, layer: Layer = Layer.classic) -> CorpusRecord:
    return CorpusRecord(
        id=rid, work_id=rid, title=title, layer=layer,
        text=text, citation_eligible=False, polarity=Polar.none,
    )


def _index() -> MemoryIndex:
    return MemoryIndex(
        [
            _rec("s", "周公解梦", "龙蛇杀人主大凶 蛇咬人主得大财 蛇入怀中生贵子 蛇行水内主迁荣"),
            _rec("b", "周公解梦", "床帐改换移居吉 床上有蚁主不祥 床帐破损妻欲亡 床上哭泣主大凶"),
            _rec(
                "p", "梦林玄解·吉凶有概",
                "若涂泞水浊，形体臭秽，口臭同床，睡觉，草木枯槁等类，凶兆也。",
                Layer.theory,
            ),
        ],
        [[1.0, 0.0], [0.9, 0.1], [0.2, 0.8]],
    )


def test_interpret_response_is_essay_and_sources() -> None:
    body = InterpretResponse(
        essay="一篇解梦",
        sources=[SourceOut(work="周公解梦", quote="蛇入怀中生贵子", channel="字面")],
        overlay=None,
        referral=None,
    )
    dumped = body.model_dump()
    assert dumped["essay"] == "一篇解梦"
    assert dumped["sources"][0]["channel"] == "字面"
    assert "verdict" not in dumped
    assert "c3" not in dumped


def test_snake_sources_include_bosom() -> None:
    out = interpret("梦见蛇入怀里", _index(), query_vec=[1.0, 0.0])
    blob = "".join(s.quote for s in out.sources)
    assert "入怀" in blob or "贵子" in blob
    assert out.referral is None
    assert out.essay == ""


def test_kouchou_sees_stink_not_only_ants() -> None:
    out = interpret(
        "我梦到我和一个喜欢我的女孩在一张床上睡觉，但是她很口臭",
        _index(),
        query_vec=[0.2, 0.8],
    )
    blob = "".join(s.quote for s in out.sources)
    assert "臭秽" in blob or "同床" in blob
    literal = [s for s in out.sources if s.channel == "字面"]
    assert literal
    assert "床上有蚁" not in literal[0].quote


def test_safety_referral_empty_essay() -> None:
    out = interpret(
        "反复噩梦让我睡不着，梦里想伤自己，醒来也还想",
        _index(),
        query_vec=[1.0, 0.0],
    )
    assert out.referral
    assert out.essay == ""
    assert out.sources == []


def test_vector_none_still_returns_snake_literal() -> None:
    out = interpret("梦见蛇入怀里", _index(), query_vec=None)
    blob = "".join(s.quote for s in out.sources)
    assert any(s.channel == "字面" for s in out.sources)
    assert "入怀" in blob or "贵子" in blob
