"""Time-range utilities for Asia/Seoul (KST) date/time handling.

Provides:
- get_time_range(hour) → Korean time-range label
- get_kst_now() → current datetime in KST
- get_kst_today() → current date in KST
- parse_date(date_str) → parsed date or today (KST), raises 422 on invalid format

Requirements: 11.1, 11.2, 11.3, 11.4
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from app.core.errors import ApiException
from app.core.time import KST, now_kst, today_kst


# Time range mapping: label → (start_hour, end_hour) inclusive
TIME_RANGES: dict[str, tuple[int, int]] = {
    "새벽": (0, 5),
    "아침": (6, 8),
    "오전": (9, 11),
    "오후": (12, 17),
    "저녁": (18, 20),
    "밤": (21, 23),
}


def get_time_range(hour: int) -> str:
    """Return the Korean time-range label for a given hour (0-23).

    The mapping is exhaustive and mutually exclusive:
    - 새벽: 0-5
    - 아침: 6-8
    - 오전: 9-11
    - 오후: 12-17
    - 저녁: 18-20
    - 밤: 21-23

    Raises ValueError if hour is outside [0, 23].
    """
    if not (0 <= hour <= 23):
        raise ValueError(f"hour must be between 0 and 23, got {hour}")

    for label, (start, end) in TIME_RANGES.items():
        if start <= hour <= end:
            return label

    # This should never be reached due to exhaustive mapping, but satisfies type checker
    raise ValueError(f"No time range found for hour {hour}")  # pragma: no cover


def get_kst_now() -> dt.datetime:
    """Return the current datetime in Asia/Seoul (KST)."""
    return now_kst()


def get_kst_today() -> dt.date:
    """Return the current date in Asia/Seoul (KST)."""
    return today_kst()


def parse_date(date_str: Optional[str]) -> dt.date:
    """Parse an ISO 8601 date string (YYYY-MM-DD) into a date object.

    - If date_str is None, returns today's date in KST.
    - If date_str is invalid, raises ApiException with 422 status.

    Requirements: 11.2, 11.3
    """
    if date_str is None:
        return get_kst_today()

    try:
        return dt.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        raise ApiException(
            status_code=422,
            code="INVALID_DATE_FORMAT",
            message="날짜 형식이 유효하지 않습니다. YYYY-MM-DD 형식을 사용해 주세요.",
            details={"field": "date", "value": date_str},
        )
