"""DateTime utilities for ZotWatch."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_today_start() -> datetime:
    """Get start of today (midnight) in UTC."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def ensure_isoformat(dt: datetime | None) -> str | None:
    """Convert datetime to ISO 8601 string."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def iso_to_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 string to datetime."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def ensure_aware(dt: datetime | None) -> datetime | None:
    """Ensure datetime is timezone-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_date(value) -> datetime | None:
    """Parse various date formats to datetime."""
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return ensure_aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            try:
                return ensure_aware(datetime.strptime(value, "%Y-%m-%d"))
            except ValueError:
                return None
    return None


__all__ = [
    "utc_now",
    "utc_today_start",
    "ensure_isoformat",
    "iso_to_datetime",
    "ensure_aware",
    "parse_date",
]
