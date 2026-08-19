import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from dreams.cite import c3_from_hits, span_match
from dreams.models import CorpusRecord, Polar


SNAKE = "蛇入怀中生贵子"
SOURCE = "龙蛇杀人主大凶 蛇咬人主得大财 蛇入怀中生贵子 蛇行水内主迁荣"


def test_span_match_requires_contiguous_source() -> None:
    rec = CorpusRecord(
        id="zg-snake",
        work_id="zhougong-jiemeng",
        title="周公解梦",
        layer="classic",
        text=SOURCE,
        citation_eligible=True,
        polarity=Polar.auspicious,
    )
    hit = span_match("蛇入怀中生贵子", rec)
    assert hit is not None
    assert hit.quote == SNAKE
    assert SOURCE[hit.start:hit.end] == SNAKE
    assert span_match("手机进镜主吉", rec) is None
    assert span_match("蛇入怀中生贵子 又加一句假的", rec) is None


def test_c3_counts_only_eligible() -> None:
    good = CorpusRecord(
        id="a", work_id="zg", title="周公", layer="classic",
        text=SOURCE, citation_eligible=True, polarity=Polar.auspicious,
    )
    bad = CorpusRecord(
        id="b", work_id="zg", title="周公", layer="classic",
        text="龙蛇杀人主大凶", citation_eligible=True, polarity=Polar.inauspicious,
    )
    ocr = CorpusRecord(
        id="c", work_id="ocr", title="OCR", layer="classic",
        text=SOURCE, citation_eligible=False, polarity=Polar.auspicious,
    )
    assert c3_from_hits([span_match(SNAKE, good)]) == "偏吉"
    assert c3_from_hits([span_match(SNAKE, good), span_match("龙蛇杀人主大凶", bad)]) == "有冲"
    assert c3_from_hits([span_match(SNAKE, ocr)]) == "说不清"
    assert c3_from_hits([]) == "说不清"
