from __future__ import annotations

import json
import struct
from pathlib import Path

from dreams.models import CorpusRecord

ROOT = Path(__file__).resolve().parents[3]
STORE_DIR = ROOT / "data" / "dream-store"


def save_store(
    root: Path,
    records: list[CorpusRecord],
    vectors: list[list[float]],
    meta: dict | None = None,
) -> None:
    if len(records) != len(vectors):
        raise ValueError("records/vectors length")
    if not records:
        raise ValueError("empty store")
    dim = len(vectors[0])
    if dim < 2 or any(len(vec) != dim for vec in vectors):
        raise ValueError("vector dim")
    root.mkdir(parents=True, exist_ok=True)
    (root / "chunks.jsonl").write_text(
        "\n".join(rec.model_dump_json() for rec in records) + "\n",
        encoding="utf-8",
    )
    packed = bytearray(struct.pack("<II", len(vectors), dim))
    for vec in vectors:
        packed.extend(struct.pack(f"<{dim}f", *vec))
    (root / "vectors.bin").write_bytes(packed)
    payload = {"n": len(records), "dim": dim, **(meta or {})}
    (root / "meta.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_store(root: Path | None = None) -> tuple[list[CorpusRecord], list[list[float]]] | None:
    base = root or STORE_DIR
    chunk_path = base / "chunks.jsonl"
    vec_path = base / "vectors.bin"
    if not chunk_path.is_file() or not vec_path.is_file():
        return None
    records = [
        CorpusRecord.model_validate(json.loads(line))
        for line in chunk_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    blob = vec_path.read_bytes()
    n, dim = struct.unpack_from("<II", blob)
    need = 8 + n * dim * 4
    if len(blob) < need or n != len(records):
        raise ValueError("store vectors mismatch")
    offset = 8
    vectors: list[list[float]] = []
    fmt = f"<{dim}f"
    width = dim * 4
    for _ in range(n):
        vectors.append(list(struct.unpack_from(fmt, blob, offset)))
        offset += width
    return records, vectors
