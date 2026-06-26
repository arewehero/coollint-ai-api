from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def now_kst() -> dt.datetime:
    return dt.datetime.now(tz=KST)


def today_kst() -> dt.date:
    return now_kst().date()
