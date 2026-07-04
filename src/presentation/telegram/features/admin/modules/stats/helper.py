from src.domain.enums.period import StatsPeriod


def period_flags(period: StatsPeriod) -> dict:
    return {
        "is_today": period == StatsPeriod.TODAY,
        "is_week": period == StatsPeriod.WEEK,
        "is_month": period == StatsPeriod.MONTH,
        "is_all": period == StatsPeriod.ALL,
        "lbl_today": ("🟢 " if period == StatsPeriod.TODAY else "") + "Сегодня",
        "lbl_week": ("🟢 " if period == StatsPeriod.WEEK else "") + "Неделя",
        "lbl_month": ("🟢 " if period == StatsPeriod.MONTH else "") + "Месяц",
        "lbl_all": ("🟢 " if period == StatsPeriod.ALL else "") + "Всё",
    }