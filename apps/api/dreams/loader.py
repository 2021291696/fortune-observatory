from __future__ import annotations

import json
from pathlib import Path

from dreams.models import CorpusRecord, Layer, Polar

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
DEFAULT_REFUSE = ("ocr-candidate", "source-scan", "public-transcript", "duanmeng")


def _refuse(path: str, needles: list[str]) -> None:
    lowered = path.replace("\\", "/").lower()
    if any(n in lowered for n in needles):
        raise ValueError(f"ineligible corpus path: {path}")


def load_records(root: Path | None = None) -> list[CorpusRecord]:
    base = root or CORPUS_DIR
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    refuse = list({*DEFAULT_REFUSE, *manifest.get("refuse_path_substrings", [])})
    out: list[CorpusRecord] = []
    for work in manifest["works"]:
        rel = work["path"]
        _refuse(rel, refuse)
        if not work.get("citation_eligible"):
            continue
        path = base / rel
        if work["kind"] == "jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = CorpusRecord.model_validate(json.loads(line))
                if not rec.citation_eligible:
                    continue
                out.append(rec)
        elif work["kind"] == "full_text":
            text = path.read_text(encoding="utf-8")
            size = int(work.get("chunk", 400))
            title = str(work.get("title") or "周公解梦")
            layer = Layer(work.get("layer") or "classic")
            edition = str(work.get("edition") or "daizhige 4a6d6f20")
            i = 0
            n = 0
            while i < len(text):
                chunk = text[i:i + size].strip()
                if chunk:
                    n += 1
                    if layer == Layer.theory:
                        polarity = Polar.none
                    elif "凶" in chunk and "吉" in chunk:
                        polarity = Polar.none
                    elif "凶" in chunk:
                        polarity = Polar.inauspicious
                    elif "吉" in chunk or "贵子" in chunk:
                        polarity = Polar.auspicious
                    else:
                        polarity = Polar.none
                    out.append(CorpusRecord(
                        id=f"{work['id']}-{n}",
                        work_id=work["id"],
                        title=title,
                        layer=layer,
                        text=chunk[:4000],
                        citation_eligible=True,
                        polarity=polarity,
                        edition=edition,
                    ))
                i += size
        else:
            raise ValueError(f"unknown kind {work['kind']}")
    if not out:
        raise ValueError("empty eligible corpus")
    return out
