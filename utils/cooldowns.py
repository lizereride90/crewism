from datetime import datetime, timedelta


def utcnow() -> datetime:
    return datetime.utcnow()


def on_cooldown(expires_at: datetime | None) -> bool:
    if not expires_at:
        return False
    return utcnow() < expires_at


def cooldown_seconds_left(expires_at: datetime) -> int:
    return max(0, int((expires_at - utcnow()).total_seconds()))


def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"
