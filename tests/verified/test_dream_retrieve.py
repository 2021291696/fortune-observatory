import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from dreams.index import MemoryIndex
from dreams.models import CorpusRecord, Layer, Polar
from dreams.retrieve import lexical_tokens, retrieve


def _rec(rid: str, title: str, text: str, layer: Layer = Layer.classic) -> CorpusRecord:
    return CorpusRecord(
        id=rid, work_id=rid, title=title, layer=layer,
        text=text, citation_eligible=False, polarity=Polar.none,
    )


SNAKE = "梦见蛇入怀里"
KOUCHOU = "我梦到我和一个喜欢我的女孩在一张床上睡觉，但是她很口臭"


def test_tokens_drop_stopwords_keep_images() -> None:
    toks = lexical_tokens(SNAKE)
    assert "梦见" not in toks
    assert "蛇入" in toks or "入怀" in toks
    assert "我" not in toks


def test_snake_lexical_hits_bosom() -> None:
    bosom = _rec("b", "周公解梦", "蛇入怀中生贵子 蛇行水内主迁荣")
    bite = _rec("a", "周公解梦", "蛇咬人主得大财")
    idx = MemoryIndex([bite, bosom], [[1.0, 0.0], [0.0, 1.0]])
    out = retrieve(SNAKE, idx, query_vec=None)
    quotes = [s.quote for s in out if s.channel == "字面"]
    assert any("入怀" in q or "贵子" in q or "男女" in q for q in quotes)
    assert all(s.channel == "字面" for s in out)


def test_kouchou_stink_outranks_ants() -> None:
    ants = _rec("ants", "周公解梦", "床上有蚁主不祥 床上哭泣主大凶")
    stink = _rec("stink", "梦林玄解·吉凶有概", "若涂泞水浊，形体臭秽，口臭同床，睡觉，草木枯槁等类，凶兆也。", Layer.theory)
    idx = MemoryIndex([ants, stink], [[1.0, 0.0], [0.0, 1.0]])
    out = retrieve(KOUCHOU, idx, query_vec=None)
    literal = [s for s in out if s.channel == "字面"]
    blob = "".join(s.quote for s in literal)
    assert "臭秽" in blob or "同床" in blob or "口臭" in blob
    assert literal, "need at least one 字面"
    assert "床上有蚁" not in literal[0].quote
    if len(literal) == 1:
        assert "床上有蚁" not in literal[0].quote


def test_merge_tags_literal_first() -> None:
    a = _rec("a", "A", "蛇入怀中生贵子")
    b = _rec("b", "B", "日间残留可以进梦")
    idx = MemoryIndex([a, b], [[1.0, 0.0], [0.0, 1.0]])
    out = retrieve(SNAKE, idx, query_vec=[0.0, 1.0])
    channels = [s.channel for s in out]
    assert "字面" in channels
    assert channels.index("字面") < channels.index("近邻") if "近邻" in channels else True
    tagged = {s.work: s.channel for s in out}
    assert tagged["A"] == "字面"
    if "B" in tagged:
        assert tagged["B"] == "近邻"


def test_empty_dream_tokens_gives_empty_without_vec() -> None:
    idx = MemoryIndex([_rec("a", "A", "蛇入怀中生贵子")], [[1.0, 0.0]])
    out = retrieve("梦见了的在", idx, query_vec=None)
    assert out == []
