import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from dreams.clean import chunk_text, clean_ocr, unwrap_prose
from dreams.models import CorpusRecord, Layer, Polar
from dreams.store import load_store, save_store


def test_clean_ocr_drops_furniture() -> None:
    raw = """# OCR candidate
## Page 1
Kodak Gray Scale
COLORCheCkeR
内閣文库
番號潢
12345678910
也夢真乎人人物物事事
境寝而见焉覺而憶之其明
A
"""
    out = clean_ocr(raw)
    assert "Kodak" not in out
    assert "12345678910" not in out
    assert "夢" in out
    assert "境寝" in out


def test_unwrap_prose_joins_wrapped_lines() -> None:
    text = "The dream\nis a test.\n\nSecond para."
    out = unwrap_prose(text)
    assert "The dream is a test." in out
    assert "Second para." in out


def test_chunk_text_respects_size() -> None:
    chunks = chunk_text("甲" * 1000, size=400)
    assert chunks
    assert all(len(item) <= 400 for item in chunks)
    assert sum(len(item) for item in chunks) >= 900


def test_store_roundtrip(tmp_path) -> None:
    rec = CorpusRecord(
        id="zg-1",
        work_id="zg",
        title="周公解梦",
        layer=Layer.classic,
        text="蛇入怀中生贵子",
        citation_eligible=True,
        polarity=Polar.auspicious,
    )
    save_store(tmp_path, [rec], [[0.25, 0.5, 0.75]])
    records, vectors = load_store(tmp_path)
    assert records[0].id == "zg-1"
    assert records[0].text == "蛇入怀中生贵子"
    assert vectors[0] == pytest.approx([0.25, 0.5, 0.75])
    blob = (tmp_path / "vectors.bin").read_bytes()
    n, dim = struct.unpack_from("<II", blob)
    assert (n, dim) == (1, 3)


def test_load_missing_store_is_none(tmp_path) -> None:
    assert load_store(tmp_path) is None
