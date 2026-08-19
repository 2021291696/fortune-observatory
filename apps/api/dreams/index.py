from __future__ import annotations

import math
from dataclasses import dataclass

from dreams.models import CorpusRecord


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _norm(a: list[float]) -> float:
    return math.sqrt(sum(x * x for x in a)) or 1.0


def cosine(a: list[float], b: list[float]) -> float:
    return _dot(a, b) / (_norm(a) * _norm(b))


@dataclass(frozen=True)
class Ranked:
    record: CorpusRecord
    score: float


class MemoryIndex:
    def __init__(self, records: list[CorpusRecord], vectors: list[list[float]]) -> None:
        if len(records) != len(vectors):
            raise ValueError("records/vectors length")
        self.records = records
        self.vectors = vectors

    def query(self, vector: list[float], k: int = 8, layers: set | None = None) -> list[Ranked]:
        pairs = zip(self.records, self.vectors)
        if layers is not None:
            pairs = [(record, vec) for record, vec in pairs if record.layer in layers]
        ranked = [Ranked(record, cosine(vector, vec)) for record, vec in pairs]
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:k]
