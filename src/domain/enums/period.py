from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from enum import Enum


MSK = ZoneInfo("Europe/Moscow")


class StatsPeriod(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"

    def label(self) -> str:
        match self:
            case StatsPeriod.TODAY:
                return "Сегодня"
            case StatsPeriod.WEEK:
                return "Неделя"
            case StatsPeriod.MONTH:
                return "Месяц"
            case StatsPeriod.ALL:
                return "Всё время"

    from zoneinfo import ZoneInfo

    def since_utc(self) -> datetime | None:
        now = datetime.now(timezone.utc)
        match self:
            case StatsPeriod.TODAY:
                now_msk = now.astimezone(MSK)
                midnight_msk = now_msk.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                return midnight_msk.astimezone(timezone.utc)
            case StatsPeriod.WEEK:
                return now - timedelta(days=7)
            case StatsPeriod.MONTH:
                return now - timedelta(days=30)
            case StatsPeriod.ALL:
                return None
