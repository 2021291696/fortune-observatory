from __future__ import annotations

import re

from dreams.index import MemoryIndex
from dreams.models import CorpusRecord, SourceOut

STOP = frozenset("梦见 一个 但是 我 的 了 在 很 和 有 是 到 这 那".split())
_HAN_RUN = re.compile(r"[一-鿿]+")
_EN = re.compile(r"[A-Za-z]{2,}")
LEX_CAP = 20
VEC_CAP = 12
MERGE_CAP = 24
QUOTE_CAP = 200


def lexical_tokens(dream: str) -> list[str]:
    out: list[str] = []
    for run in _HAN_RUN.findall(dream):
        if len(run) >= 2:
            out.extend(run[i : i + 2] for i in range(len(run) - 1))
    out.extend(word.lower() for word in _EN.findall(dream))
    return [token for token in out if token not in STOP]


def _quote(record: CorpusRecord) -> str:
    return record.text[:QUOTE_CAP]


def _lexical(dream: str, records: list[CorpusRecord]) -> list[CorpusRecord]:
    tokens = lexical_tokens(dream)
    if not tokens:
        return []
    scored: list[tuple[int, CorpusRecord]] = []
    for record in records:
        hits = sum(1 for token in tokens if token in record.text)
        if hits:
            scored.append((hits, record))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return [record for _, record in scored[:LEX_CAP]]


def _vector(index: MemoryIndex, query_vec: list[float] | None) -> list[CorpusRecord]:
    if query_vec is None:
        return []
    return [item.record for item in index.query(query_vec, k=VEC_CAP)]


def retrieve(
    dream: str,
    index: MemoryIndex,
    query_vec: list[float] | None,
) -> list[SourceOut]:
    literal = _lexical(dream, index.records)
    neighbor = _vector(index, query_vec)
    channel: dict[str, str] = {}
    ordered: list[CorpusRecord] = []
    for record in literal:
        if record.id not in channel:
            channel[record.id] = "字面"
            ordered.append(record)
    for record in neighbor:
        if record.id not in channel:
            channel[record.id] = "近邻"
            ordered.append(record)
    return [
        SourceOut(work=record.title, quote=_quote(record), channel=channel[record.id])
        for record in ordered[:MERGE_CAP]
    ]
