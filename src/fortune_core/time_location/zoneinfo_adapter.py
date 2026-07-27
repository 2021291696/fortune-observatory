from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class CivilTimeError(ValueError):
    """A wall-clock time cannot be resolved without inventing an instant."""


def normalize_civil_time(local: datetime, timezone_id: str, fold: int | None = None) -> datetime:
    """Resolve a naive civil time with explicit DST-gap and overlap handling.

    A valid instant must round-trip from local -> UTC -> local. Two valid offsets
    indicate an overlap and require `fold`; zero valid offsets indicate a gap.
    """
    if local.tzinfo is not None:
        raise CivilTimeError("civil wall time must be naive; provide timezone_id separately")
    if fold not in (None, 0, 1):
        raise CivilTimeError("fold must be 0, 1, or omitted")
    try:
        zone = ZoneInfo(timezone_id)
    except ZoneInfoNotFoundError as error:
        raise CivilTimeError(f"unknown IANA timezone: {timezone_id}") from error

    candidates: list[tuple[int, datetime]] = []
    for candidate_fold in (0, 1):
        candidate = local.replace(tzinfo=zone, fold=candidate_fold)
        round_trip = candidate.astimezone(UTC).astimezone(zone)
        if round_trip.replace(tzinfo=None) == local:
            candidates.append((candidate_fold, candidate))
    distinct_offsets = {candidate.utcoffset() for _, candidate in candidates}
    if not candidates:
        raise CivilTimeError("nonexistent local time due to a daylight-saving transition")
    if len(distinct_offsets) > 1:
        if fold is None:
            raise CivilTimeError("ambiguous local time requires an explicit fold of 0 or 1")
        return next(candidate for item_fold, candidate in candidates if item_fold == fold)
    return candidates[0][1]
