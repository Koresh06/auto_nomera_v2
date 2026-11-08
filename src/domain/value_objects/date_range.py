import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from src.domain.enums.period import MSK

_DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")


@dataclass(frozen=True, slots=True)
class DateRange:
    """Период по датам включительно, в московском времени — как и
    «Сегодня» в :class:`StatsPeriod`."""

    start: date
    end: date

    @classmethod
    def parse(cls, raw: str, *, today: date | None = None) -> "DateRange":
        """«01.10.2026 - 31.10.2026» или одна дата. ValueError при ошибке."""
        found = _DATE_RE.findall(raw)
        leftovers = re.sub(r"[\s\-–—по]", "", _DATE_RE.sub("", raw.lower()))
        if len(found) not in (1, 2) or leftovers:
            raise ValueError("Ожидается формат 01.10.2026 - 31.10.2026")

        start = datetime.strptime(found[0], "%d.%m.%Y").date()
        end = datetime.strptime(found[-1], "%d.%m.%Y").date()
        if start > end:
            raise ValueError("Начало периода позже конца")
        today = today or datetime.now(MSK).date()
        if start > today:
            raise ValueError("Период начинается в будущем")
        return cls(start=start, end=end)

    def bounds_utc(self) -> tuple[datetime, datetime]:
        """[начало первого дня; начало следующего за последним днём)."""
        since = datetime.combine(self.start, time.min, tzinfo=MSK)
        until = datetime.combine(self.end + timedelta(days=1), time.min, tzinfo=MSK)
        return since.astimezone(timezone.utc), until.astimezone(timezone.utc)

    @property
    def label(self) -> str:
        return f"{self.start:%d.%m.%Y} — {self.end:%d.%m.%Y}"
