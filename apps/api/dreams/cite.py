from __future__ import annotations

from dreams.models import CorpusRecord, Polar, SpanHit


def span_match(quote: str, record: CorpusRecord) -> SpanHit | None:
    needle = quote.strip()
    if len(needle) < 4 or not record.citation_eligible:
        return None
    start = record.text.find(needle)
    if start < 0:
        return None
    return SpanHit(
        record_id=record.id,
        work_id=record.work_id,
        title=record.title,
        quote=needle,
        start=start,
        end=start + len(needle),
        layer=record.layer,
        polarity=record.polarity,
        quote_zh_is_paraphrase=record.quote_zh_is_paraphrase,
    )


def c3_from_hits(hits: list[SpanHit | None]) -> str:
    poles = {h.polarity for h in hits if h is not None}
    poles.discard(Polar.none)
    poles.discard(Polar.mixed)
    if not poles:
        return "说不清"
    if poles == {Polar.auspicious}:
        return "偏吉"
    return "有冲"
