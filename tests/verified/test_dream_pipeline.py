import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from dreams.index import MemoryIndex
from dreams.models import CorpusRecord, Layer, Polar

try:
    from dreams.pipeline import interpret, _pick_quote
except ImportError:
    interpret = None
    _pick_quote = None


def _index() -> MemoryIndex:
    snake = CorpusRecord(
        id="s", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="龙蛇杀人主大凶 蛇咬人主得大财 蛇入怀中生贵子 蛇行水内主迁荣",
        citation_eligible=True, polarity=Polar.auspicious,
    )
    day = CorpusRecord(
        id="d", work_id="fr", title="The Interpretation of Dreams", layer=Layer.science,
        text="The day's residues, as we shall find, are not the dream itself, but they furnish the dream-work with material.",
        citation_eligible=True, polarity=Polar.none,
    )
    return MemoryIndex(records=[snake, day], vectors=[[1.0, 0.0], [0.0, 1.0]])


def test_snake_fixture_cites_zhougong() -> None:
    out = interpret("梦见蛇钻进怀里", _index(), query_vec=[1.0, 0.0], essay_fn=lambda **k: None)
    quotes = [c.quote for c in out.citations]
    assert any("蛇入怀中生贵子" in q for q in quotes)
    assert out.c3 == "偏吉"
    assert out.fortune is not None
    assert out.scene
    assert "应期" not in (out.verdict + out.fortune.start)
    assert out.overlay is None


def test_day_residue_fixture_cites_freud_not_as_classic() -> None:
    out = interpret("白天开会的事晚上又做了一遍", _index(), query_vec=[0.0, 1.0], essay_fn=lambda **k: None)
    assert out.science
    assert all(c.work != "周公解梦" for c in out.citations) or out.c3 == "说不清"


def test_unrelated_dream_does_not_promote_neighbors() -> None:
    out = interpret(
        "我梦见自己在数楼梯台阶", _index(), query_vec=[0.5, 0.5],
        essay_fn=lambda **k: None, min_score=0.85,
    )
    assert "蛇入怀中生贵子" not in "".join(c.quote for c in out.citations)
    assert out.miss == "本地可核验梦书没有这一象"
    assert "天下梦书都没有" not in (out.verdict + (out.miss or ""))


def test_safety_referral_short_circuits_symbolism() -> None:
    out = interpret(
        "反复噩梦让我睡不着，梦里想伤自己，醒来也还想",
        _index(), query_vec=[1.0, 0.0], essay_fn=lambda **k: None,
    )
    assert out.referral
    assert "蛇入怀" not in out.verdict


def test_single_shared_char_is_not_a_citation() -> None:
    junk = CorpusRecord(
        id="j", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="行胭脂粉主生女 食蒜者有灾害事 女人拔刀主有子 抱小儿女主口舌",
        citation_eligible=True, polarity=Polar.auspicious,
    )
    snake = CorpusRecord(
        id="s", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="蛇入怀中生贵子",
        citation_eligible=True, polarity=Polar.auspicious,
    )
    assert _pick_quote("和喜欢的女孩同床她有口臭但没有发生关系", junk) is None
    assert _pick_quote("梦见蛇钻进怀里", snake) == "蛇入怀中生贵子"
    tongue = CorpusRecord(
        id="t", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="见手帕主有口舌 与人饮酒有口舌",
        citation_eligible=True, polarity=Polar.mixed,
    )
    assert _pick_quote("她有口臭但没有发生关系", tongue) is None


def test_generic_bed_line_is_not_a_citation() -> None:
    bed = CorpusRecord(
        id="b", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="床帐改换移居吉 床上有蚁主不祥 床帐破损妻欲亡 床上哭泣主大凶",
        citation_eligible=True, polarity=Polar.inauspicious,
    )
    dream = "我梦到我和一个喜欢我的女孩在一张床上睡觉，但是她很口臭"
    assert _pick_quote(dream, bed) is None
    snake = CorpusRecord(
        id="s", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="蛇入怀中生贵子",
        citation_eligible=True, polarity=Polar.auspicious,
    )
    assert _pick_quote("梦见蛇钻进怀里", snake) == "蛇入怀中生贵子"


from dreams.models import Layer


def _full_index() -> MemoryIndex:
    snake = CorpusRecord(
        id="s", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="龙蛇杀人主大凶 蛇咬人主得大财 蛇入怀中生贵子 蛇行水内主迁荣",
        citation_eligible=True, polarity=Polar.auspicious,
    )
    bed = CorpusRecord(
        id="b", work_id="zg", title="周公解梦", layer=Layer.classic,
        text="床帐改换移居吉 床上有蚁主不祥 床帐破损妻欲亡 床上哭泣主大凶",
        citation_eligible=True, polarity=Polar.inauspicious,
    )
    principle = CorpusRecord(
        id="p", work_id="menglin-principle", title="梦林玄解·吉凶有概",
        layer=Layer.theory,
        text="若涂泞水浊，形体臭秽，草木枯槁等类，凶兆也。",
        citation_eligible=True, polarity=Polar.none,
    )
    lung = CorpusRecord(
        id="l", work_id="lingshu-yinxie", title="灵枢·淫邪发梦",
        layer=Layer.theory,
        text="客于肺，则梦飞扬，见金铁之器；盛者，则梦见恐惧畏怖。",
        citation_eligible=True, polarity=Polar.none,
    )
    return MemoryIndex(
        records=[snake, bed, principle, lung],
        vectors=[[1.0, 0.0], [0.9, 0.1], [0.2, 0.8], [0.1, 0.9]],
    )


KOUCHOU = "我梦到我和一个喜欢我的女孩在一张床上睡觉，但是她很口臭"


def test_kouchou_has_no_direct_cite_but_has_assoc() -> None:
    out = interpret(KOUCHOU, _full_index(), query_vec=[0.2, 0.8], essay_fn=lambda **k: None)
    blob = "".join(c.quote for c in out.citations)
    assert "床上有蚁" not in blob
    assert "床上哭泣" not in blob
    assert out.citations == []
    assert out.miss == "本地可核验梦书没有这一象"
    assert out.associations
    assert all(item.note == "联想，不是占梦原断" for item in out.associations)
    assoc = "".join(item.quote for item in out.associations)
    assert "形体臭秽" in assoc or "客于肺" in assoc
    assert out.c3 == "说不清"


def test_snake_direct_cite_ignores_theory_for_c3() -> None:
    out = interpret("梦见蛇钻进怀里", _full_index(), query_vec=[1.0, 0.0], essay_fn=lambda **k: None)
    assert any("蛇入怀中生贵子" in c.quote for c in out.citations)
    assert out.c3 == "偏吉"


def test_snake_prefers_bosom_over_generic_snake() -> None:
    leave = CorpusRecord(
        id="a", work_id="dh", title="敦煌本梦书·蛇", layer=Layer.classic,
        text="梦见蛇远人去，必富。", citation_eligible=True, polarity=Polar.none,
    )
    bosom = CorpusRecord(
        id="b", work_id="dh", title="敦煌本梦书·蛇", layer=Layer.classic,
        text="梦见蛇入怀，有贵子。", citation_eligible=True, polarity=Polar.auspicious,
    )
    door = CorpusRecord(
        id="c", work_id="dh", title="敦煌本梦书·蛇", layer=Layer.classic,
        text="梦见避蛇入门者，得财。", citation_eligible=True, polarity=Polar.none,
    )
    idx = MemoryIndex([leave, bosom, door], [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    out = interpret("梦见蛇钻进怀里", idx, [1.0, 0.0], essay_fn=lambda **k: None)
    blob = "".join(c.quote for c in out.citations)
    assert "蛇入怀" in blob
    assert "远人去" not in blob
    assert "避蛇入门" not in blob


def test_like_does_not_fire_xi_assoc() -> None:
    joy = CorpusRecord(
        id="j", work_id="qf", title="潜夫论·梦列", layer=Layer.theory,
        text="凡察梦之大体：清絜鲜好，貌坚健，皆为吉喜。", citation_eligible=True, polarity=Polar.none,
    )
    stink = CorpusRecord(
        id="s", work_id="ml", title="梦林玄解·吉凶有概", layer=Layer.theory,
        text="若涂泞水浊，形体臭秽，草木枯槁等类，凶兆也。", citation_eligible=True, polarity=Polar.none,
    )
    idx = MemoryIndex([joy, stink], [[1.0, 0.0], [0.0, 1.0]])
    out = interpret(KOUCHOU, idx, [1.0, 0.0], essay_fn=lambda **k: None)
    assoc = "".join(item.quote for item in out.associations)
    assert "形体臭秽" in assoc
    assert "吉喜" not in assoc


def test_day_work_does_not_cite_did_nightmare() -> None:
    omen = CorpusRecord(
        id="o", work_id="dh", title="敦煌本梦书", layer=Layer.classic,
        text="廣東東莞一帶，如人們做了惡夢，早晨便用紅紙寫上一行字，便可驅夢：弓弩相斗生争论",
        citation_eligible=True, polarity=Polar.mixed,
    )
    freud = CorpusRecord(
        id="f", work_id="fr", title="The Interpretation of Dreams", layer=Layer.science,
        text="The day remnants penetrate abundantly into the dream.",
        citation_eligible=True, polarity=Polar.none, quote_zh_is_paraphrase=True,
    )
    idx = MemoryIndex([omen, freud], [[1.0, 0.0], [0.0, 1.0]])
    out = interpret("白天开会争论的事，晚上又原样做了一遍", idx, [1.0, 0.0], essay_fn=lambda **k: None)
    assert out.citations == []
    assert out.science
    assert "驅夢" not in (out.verdict or "")


from dreams.models import InterpretResponse, SourceOut


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
    assert "scene" not in dumped
    assert "verdict" not in dumped
    assert "c3" not in dumped
    assert "citations" not in dumped
    assert "associations" not in dumped
    assert "fortune" not in dumped
    assert "science" not in dumped
    assert "miss" not in dumped
