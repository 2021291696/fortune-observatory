import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from dreams.embed import EmbedError, embed_texts
from dreams.index import MemoryIndex
from dreams.models import CorpusRecord, Layer, Polar


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def post(self, url: str, json: dict, headers: dict, timeout: float):
        self.calls.append(json)
        assert "texts" in json
        assert json["model"] == "embo-01"
        assert json["type"] in {"db", "query"}
        assert "input" not in json
        n = len(json["texts"])
        return httpx.Response(200, json={"vectors": [[1.0, 0.0]] * n, "base_resp": {"status_code": 0}})


def test_embed_payload_shape() -> None:
    fake = FakeClient()
    vecs = embed_texts(["蛇入怀"], kind="query", post=fake.post, api_key="x")
    assert vecs == [[1.0, 0.0]]
    assert fake.calls[0]["type"] == "query"
    with pytest.raises(EmbedError):
        embed_texts(
            ["a"],
            kind="db",
            post=lambda *a, **k: httpx.Response(
                200, json={"vectors": [[1.0]], "base_resp": {"status_code": 2013}}
            ),
            api_key="x",
        )


def test_index_orders_by_cosine() -> None:
    a = CorpusRecord(
        id="s", work_id="zg", title="周公", layer=Layer.classic,
        text="蛇入怀中生贵子", citation_eligible=True, polarity=Polar.auspicious,
    )
    b = CorpusRecord(
        id="d", work_id="fr", title="Freud", layer=Layer.science,
        text="day residue", citation_eligible=True, polarity=Polar.none,
    )
    index = MemoryIndex(records=[a, b], vectors=[[1.0, 0.0], [0.0, 1.0]])
    ranked = index.query([0.99, 0.01], k=2)
    assert [h.record.id for h in ranked] == ["s", "d"]
    assert ranked[0].score > ranked[1].score
