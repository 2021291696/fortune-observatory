from datetime import date, datetime, time

from fortune_core.models import BaziSnapshot, GreatLuckPeriod

from .service import calculate_bazi


def active_great_luck(snapshot: BaziSnapshot, transit_date: date) -> GreatLuckPeriod | None:
    """Select a decade at the same local-noon convention as transit layers."""
    target = datetime.combine(
        transit_date,
        time(12),
        tzinfo=snapshot.calculation_datetime.tzinfo,
    )
    return next(
        (
            period
            for period in snapshot.great_luck_periods
            if period.start_datetime <= target < period.end_datetime
        ),
        None,
    )

__all__ = ["active_great_luck", "calculate_bazi"]
