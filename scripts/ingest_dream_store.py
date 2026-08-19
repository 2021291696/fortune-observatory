from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from dreams.clean import chunk_text, clean_ocr, unwrap_prose
from dreams.embed import embed_texts
from dreams.loader import load_records
from dreams.models import CorpusRecord, Layer, Polar
from dreams.store import STORE_DIR, load_store, save_store

NOTES = Path(r"D:\MyAIWorkspace\notes\读书\解梦")
BATCH = 16
CHUNK = 1200


def _load_dotenv() -> None:
    for path in (ROOT / ".env", Path(r"D:\MyAIWorkspace") / ".env"):
        if not path.is_file() or path.stat().st_size == 0:
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, _, value = raw.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _chunks(work_id: str, title: str, layer: Layer, text: str, eligible: bool, edition: str) -> list[CorpusRecord]:
    out: list[CorpusRecord] = []
    for i, piece in enumerate(chunk_text(text, CHUNK), start=1):
        out.append(CorpusRecord(
            id=f"{work_id}-{i}",
            work_id=work_id,
            title=title,
            layer=layer,
            text=piece[:4000],
            citation_eligible=eligible,
            polarity=Polar.none if layer != Layer.classic else (
                Polar.none if ("吉" in piece and "凶" in piece)
                else Polar.inauspicious if "凶" in piece
                else Polar.auspicious if ("吉" in piece or "贵子" in piece)
                else Polar.none
            ),
            edition=edition,
            quote_zh_is_paraphrase=layer == Layer.science,
        ))
    return out


def build_records() -> tuple[list[CorpusRecord], dict]:
    records = list(load_records())
    extra: list[CorpusRecord] = []
    extra += _chunks(
        "freud-full",
        "The Interpretation of Dreams",
        Layer.note,
        unwrap_prose((NOTES / "Freud-The-Interpretation-of-Dreams-1913.txt").read_text(encoding="utf-8")),
        False,
        "Brill 1913 cleaned",
    )
    extra += _chunks(
        "menglin-scan",
        "梦林玄解",
        Layer.note,
        clean_ocr((NOTES / "梦林玄解-OCR候选.txt").read_text(encoding="utf-8")),
        False,
        "review-only scan transcript",
    )
    extra += _chunks(
        "mengzhan-scan",
        "梦占类考",
        Layer.note,
        clean_ocr((NOTES / "梦占类考-OCR候选.txt").read_text(encoding="utf-8")),
        False,
        "review-only scan transcript",
    )
    secret = NOTES / "断梦秘书-未核验摘录.md"
    extra += _chunks(
        "duanmeng",
        "断梦秘书",
        Layer.note,
        clean_ocr(secret.read_text(encoding="utf-8")),
        False,
        "unverified web excerpt",
    )
    seen = {rec.text for rec in records}
    added = [rec for rec in extra if rec.text not in seen]
    all_recs = records + added
    counts = Counter(rec.work_id for rec in all_recs)
    meta = {
        "eligible": sum(1 for rec in all_recs if rec.citation_eligible),
        "review_only": sum(1 for rec in all_recs if not rec.citation_eligible),
        "works": dict(counts),
        "skipped_binaries": [
            "梦林玄解-明崇祯刻本扫描.pdf",
            "梦占类考-明万历刻本扫描.pdf",
            "Freud-The-Interpretation-of-Dreams-1913.epub",
            "Freud-Die-Traumdeutung.epub",
        ],
    }
    return all_recs, meta


def main() -> None:
    _load_dotenv()
    records, meta = build_records()
    print(json.dumps({"chunks": len(records), **meta}, ensure_ascii=False))
    if "--chunks-only" in sys.argv:
        save_store(STORE_DIR, records, [[0.0, 0.0]] * len(records), meta | {"vectors": False})
        (STORE_DIR / "vectors.bin").unlink(missing_ok=True)
        return
    start = 0
    vectors: list[list[float]] = []
    existing = load_store(STORE_DIR)
    ids = [rec.id for rec in records]
    if existing is not None:
        old_recs, old_vecs = existing
        old_ids = [rec.id for rec in old_recs]
        if old_ids and ids[:len(old_ids)] == old_ids and len(old_vecs) < len(records):
            vectors = old_vecs
            start = len(old_vecs)
            print(f"resume {start}/{len(records)}", flush=True)
    for i in range(start, len(records), BATCH):
        batch = [rec.text for rec in records[i:i + BATCH]]
        print(f"embed {i + 1}-{i + len(batch)}/{len(records)}", flush=True)
        vectors.extend(embed_texts(batch, kind="db", timeout=60.0))
        save_store(STORE_DIR, records[:len(vectors)], vectors, meta | {"vectors": False, "partial": len(vectors)})
    save_store(STORE_DIR, records, vectors, meta | {"vectors": True, "model": "embo-01"})
    print(f"wrote {STORE_DIR}")


if __name__ == "__main__":
    main()
