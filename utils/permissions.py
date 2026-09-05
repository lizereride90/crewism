def is_valid_name(name: str, max_len: int = 32) -> bool:
    name = (name or "").strip()
    if not 2 <= len(name) <= max_len:
        return False
    if "@" in name or "http" in name.lower():
        return False
    return True


def clamp_amount(amount: int, low: int = 1, high: int = 1_000_000) -> int:
    try:
        a = int(amount)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, a))


def safe_filename(name: str) -> str:
    keep = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
    return keep[:64] or "card"
