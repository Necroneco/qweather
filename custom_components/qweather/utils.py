"""Utils"""


def int_or_none(s: int | None) -> int | None:
    return None if s is None else int(s)


def float_or_none(s: str | None) -> float | None:
    return None if s is None else float(s)
