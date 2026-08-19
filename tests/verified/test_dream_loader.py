import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from dreams.loader import load_records


def test_loader_includes_snake_and_day_residue() -> None:
    recs = load_records()
    texts = "\n".join(r.text for r in recs if r.citation_eligible)
    assert "蛇入怀中生贵子" in texts
    assert "remnants of trivial experiences" in texts or "day remnants" in texts.lower()
    assert all(r.citation_eligible for r in recs)


CHAPTERS = {
    "lingshu-yinxie.txt": "正邪从外袭内",
    "qianfu-menglie.txt": "有直，有象",
    "liezi-zhoumu-meng.txt": "觉有八征",
    "zhouli-zhanmeng.txt": "占梦掌其岁时",
}


def test_loader_theory_chapters_present() -> None:
    from dreams.loader import CORPUS_DIR, load_records
    for name, needle in CHAPTERS.items():
        text = (CORPUS_DIR / name).read_text(encoding="utf-8")
        assert needle in text
        assert len(text) >= 40
    recs = load_records()
    titles = {r.title for r in recs if r.layer.value == "theory"}
    assert "灵枢·淫邪发梦" in titles
    assert "潜夫论·梦列" in titles
    assert "列子·周穆王" in titles
    assert "周礼·春官·占梦" in titles
    assert all(r.polarity.value == "none" or r.layer.value != "theory" for r in recs)


def test_loader_has_labelled_excerpts() -> None:
    recs = load_records()
    classics = [r for r in recs if r.layer.value == "classic"]
    theories = [r for r in recs if r.layer.value == "theory"]
    classic_text = "\n".join(r.text for r in classics)
    theory_text = "\n".join(r.text for r in theories)
    assert "梦见蛇入怀" in classic_text or "蛇入怀" in classic_text
    assert "見蛇入床下重病" in classic_text or "见蛇入床下重病" in classic_text
    assert any(r.title == "敦煌本梦书" for r in classics)
    assert "形体臭秽" in theory_text
    assert "不占有五" in theory_text
    assert "不验有五" in theory_text
    assert "俄见白日" in theory_text
    assert "燔焫" in "\n".join(r.text for r in recs)
    assert "tremendous work of condensation" in "\n".join(r.text for r in recs)
    assert "ocr" not in "".join(r.edition.lower() for r in recs)


def test_loader_refuses_ocr_and_raw_scan_names(tmp_path, monkeypatch) -> None:
    from dreams import loader
    bad = tmp_path / "ocr-candidates"
    bad.mkdir()
    (bad / "meng-lin-raw-ocr-candidate.txt").write_text("蛇入怀中生贵子", encoding="utf-8")
    monkeypatch.setattr(loader, "CORPUS_DIR", tmp_path)
    (tmp_path / "manifest.json").write_text(
        '{"works":[{"id":"ocr","path":"ocr-candidates/meng-lin-raw-ocr-candidate.txt","citation_eligible":true}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ineligible"):
        load_records()
