from __future__ import annotations

import os
from typing import Callable, Literal

import httpx

EMBED_URL = os.environ.get("FORTUNE_EMBED_URL", "https://api.minimaxi.com/v1/embeddings")
EMBED_MODEL = "embo-01"
Kind = Literal["db", "query"]
PostFn = Callable[..., httpx.Response]


class EmbedError(RuntimeError):
    pass


def embed_texts(
    texts: list[str],
    *,
    kind: Kind,
    api_key: str | None = None,
    post: PostFn | None = None,
    timeout: float = 20.0,
) -> list[list[float]]:
    if kind not in {"db", "query"}:
        raise EmbedError("type must be db or query")
    key = api_key or os.environ.get("FORTUNE_AI_API_KEY") or os.environ.get("MINIMAX_KEY") or ""
    if not key:
        raise EmbedError("missing embedding key")
    sender = post or httpx.post
    response = sender(
        EMBED_URL,
        json={"model": EMBED_MODEL, "texts": texts, "type": kind},
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    payload = response.json()
    if payload.get("base_resp", {}).get("status_code", 0) != 0:
        raise EmbedError("embed failed")
    vectors = payload.get("vectors")
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise EmbedError("vectors mismatch")
    return vectors
