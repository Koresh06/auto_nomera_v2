"""Реестр разделов выгрузки. Новый раздел = значение ReportSection, запись в
SECTIONS и запрос в репозитории; диалог и Excel подхватят его сами."""

from dataclasses import dataclass

from src.application.dtos.stats_report import ColumnKind, ReportColumn
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.balance import BalanceTransactionKind
from src.domain.enums.payment import PaymentMethod, PaymentPurpose
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.enums.report import ReportSection
from src.domain.enums.role import UserRole

METHOD_LABELS = {
    PaymentMethod.MANUAL_CARD: "Карта (вручную)",
    PaymentMethod.CRYPTO: "Криптовалюта",
    PaymentMethod.TELEGRAM_STARS: "Telegram Stars",
    PaymentMethod.YOOKASSA: "ЮKassa",
}
PURPOSE_LABELS = {
    PaymentPurpose.BALANCE_TOPUP: "Пополнение баланса",
    PaymentPurpose.PUBLICATION_SERVICE: "Услуга",
    PaymentPurpose.PRE_PUBLICATION: "Подписка",
    PaymentPurpose.SLOT: "Платный слот",
}
KIND_LABELS = {
    BalanceTransactionKind.TOPUP: "Пополнение",
    BalanceTransactionKind.COMPENSATION: "Возврат платежа на баланс",
    BalanceTransactionKind.ADMIN_CREDIT: "Начисление админом",
    BalanceTransactionKind.ADMIN_DEBIT: "Списание админом",
    BalanceTransactionKind.SLOT_PURCHASE: "Покупка слота",
    BalanceTransactionKind.SERVICE_PURCHASE: "Покупка услуги",
    BalanceTransactionKind.PRE_PUBLICATION_PURCHASE: "Покупка подписки",
}
AD_TYPE_LABELS = {
    AdType.SALE: "Продажа",
    AdType.BUY: "Покупка",
    AdType.URGENT_BUYOUT: "Срочный выкуп",
    AdType.STORE: "Магазин",
}
AD_STATUS_LABELS = {
    AdStatus.DRAFT: "Черновик",
    AdStatus.PENDING_MODERATION: "На модерации",
    AdStatus.READY: "Готово",
    AdStatus.SCHEDULED: "Запланировано",
    AdStatus.PUBLISHED: "Опубликовано",
    AdStatus.ARCHIVED: "В архиве",
}
PUBLICATION_STATUS_LABELS = {
    PublicationStatus.DRAFT: "Черновик",
    PublicationStatus.AWAITING_PAYMENT: "Ждёт оплаты",
    PublicationStatus.SCHEDULED: "Запланировано",
    PublicationStatus.PUBLISHING: "Публикуется",
    PublicationStatus.PUBLISHED: "Опубликовано",
    PublicationStatus.FAILED: "Ошибка",
    PublicationStatus.CANCELED: "Отменено",
    PublicationStatus.REPLACED: "Вытеснено",
}
SERVICE_TYPE_LABELS = {
    PublicationServiceType.AUTOPUBLISH: "Автопубликация",
    PublicationServiceType.PRIORITY_PUBLISH: "Вне очереди",
    PublicationServiceType.PIN: "Закрепление",
    PublicationServiceType.HIGHLIGHT: "Выделение",
    PublicationServiceType.PRE_PUBLICATION: "Объявления до публикации",
}
SERVICE_STATUS_LABELS = {
    PublicationServiceStatus.ACTIVE: "Активна",
    PublicationServiceStatus.USED: "Использована",
    PublicationServiceStatus.CANCELED: "Отменена",
    PublicationServiceStatus.EXPIRED: "Просрочена",
}
ROLE_LABELS = {UserRole.USER: "Пользователь", UserRole.ADMIN: "Админ"}


def _label(labels: dict):
    return lambda value: labels.get(value, getattr(value, "value", value))


def _metric(key: str, title: str, group: str, kind=ColumnKind.INT) -> ReportColumn:
    return ReportColumn(key, title, kind, group=group)


_MONEY = ColumnKind.MONEY

METRIC_COLUMNS: tuple[ReportColumn, ...] = (
    _metric("revenue_total", "Выручка всего, руб.", "Выручка", _MONEY),
    _metric("revenue_count", "Покупок", "Выручка"),
    _metric("revenue_direct", "Оплачено напрямую, руб.", "Выручка", _MONEY),
    _metric("revenue_from_balance", "Оплачено с баланса, руб.", "Выручка", _MONEY),
    _metric("revenue_slot", "Платные слоты, руб.", "Выручка", _MONEY),
    _metric("revenue_publication_service", "Услуги, руб.", "Выручка", _MONEY),
    _metric("revenue_pre_publication", "Подписка, руб.", "Выручка", _MONEY),
    _metric("inflow_total", "Поступило всего, руб.", "Поступления", _MONEY),
    _metric("inflow_count", "Успешных оплат", "Поступления"),
    _metric("topup_total", "Из них пополнения баланса, руб.", "Поступления", _MONEY),
    *(
        _metric(f"inflow_{m.value}", f"{label}, руб.", "Поступления", _MONEY)
        for m, label in METHOD_LABELS.items()
    ),
    _metric("balance_now", "Остатки на балансах сейчас, руб.", "Балансы", _MONEY),
    _metric("balance_admin_credit", "Начислено админами, руб.", "Балансы", _MONEY),
    _metric("balance_admin_debit", "Списано админами, руб.", "Балансы", _MONEY),
    _metric("balance_compensation", "Возвращено на баланс, руб.", "Балансы", _MONEY),
    _metric("users_new", "Новых пользователей", "Пользователи"),
    _metric("users_total", "Всего сейчас", "Пользователи"),
    _metric("users_blocked", "Заблокировано сейчас", "Пользователи"),
    _metric("ads_new", "Новых объявлений", "Объявления"),
    *(
        _metric(f"ads_{t.value}", label, "Объявления")
        for t, label in AD_TYPE_LABELS.items()
    ),
    _metric("publications_total", "Публикаций", "Публикации"),
    *(
        _metric(f"publications_{s.value}", label, "Публикации")
        for s, label in PUBLICATION_STATUS_LABELS.items()
    ),
    _metric("services_total", "Подключено услуг", "Услуги"),
    _metric("services_amount", "Сумма по услугам, руб.", "Услуги", _MONEY),
    *(
        _metric(f"services_{t.value}", label, "Услуги")
        for t, label in SERVICE_TYPE_LABELS.items()
    ),
)

_TG_ID = ReportColumn("tg_id", "Telegram ID", ColumnKind.INT, personal=True)
_USERNAME = ReportColumn("username", "Username", personal=True)
_FULL_NAME = ReportColumn("full_name", "Имя", personal=True)
_USER_ID = ReportColumn("user_id", "ID пользователя", ColumnKind.INT)
_REGION = ReportColumn("region", "Регион")


@dataclass(frozen=True, slots=True)
class SectionDef:
    title: str
    columns: tuple[ReportColumn, ...] = ()


SUMMARY_COLUMNS = (
    ReportColumn("group", "Группа"),
    ReportColumn("metric", "Показатель"),
    ReportColumn("value", "Значение", ColumnKind.MONEY),
)

SECTIONS: dict[ReportSection, SectionDef] = {
    ReportSection.SUMMARY: SectionDef("Сводка", SUMMARY_COLUMNS),
    ReportSection.REGIONS: SectionDef("По регионам", (_REGION, *METRIC_COLUMNS)),
    ReportSection.PAYMENTS: SectionDef(
        "Платежи",
        (
            ReportColumn("id", "ID", ColumnKind.INT),
            ReportColumn("paid_at", "Дата оплаты", ColumnKind.DATETIME),
            _REGION,
            _USER_ID,
            _TG_ID,
            _USERNAME,
            _FULL_NAME,
            ReportColumn("phone", "Телефон", personal=True),
            ReportColumn("method", "Способ", transform=_label(METHOD_LABELS)),
            ReportColumn("purpose", "Назначение", transform=_label(PURPOSE_LABELS)),
            ReportColumn("amount", "Сумма", ColumnKind.MONEY),
            ReportColumn("currency", "Валюта"),
            ReportColumn("compensated", "Возвращён на баланс", ColumnKind.BOOL),
            ReportColumn("description", "Описание"),
            ReportColumn("external_id", "Внешний ID"),
        ),
    ),
    ReportSection.BALANCE: SectionDef(
        "Операции с балансом",
        (
            ReportColumn("id", "ID", ColumnKind.INT),
            ReportColumn("created_at", "Дата", ColumnKind.DATETIME),
            _REGION,
            _USER_ID,
            _TG_ID,
            _USERNAME,
            ReportColumn("kind", "Операция", transform=_label(KIND_LABELS)),
            ReportColumn("amount", "Сумма", ColumnKind.MONEY),
            ReportColumn("balance_after", "Остаток", ColumnKind.MONEY, personal=True),
            ReportColumn("description", "Описание"),
            ReportColumn("payment_id", "ID платежа", ColumnKind.INT),
            ReportColumn("publication_id", "ID публикации", ColumnKind.INT),
        ),
    ),
    ReportSection.USERS: SectionDef(
        "Пользователи",
        (
            ReportColumn("id", "ID", ColumnKind.INT),
            _TG_ID,
            _USERNAME,
            _FULL_NAME,
            ReportColumn("phone", "Телефон", personal=True),
            _REGION,
            ReportColumn("created_at", "Регистрация", ColumnKind.DATETIME),
            ReportColumn("role", "Роль", transform=_label(ROLE_LABELS)),
            ReportColumn("is_blocked", "Заблокирован", ColumnKind.BOOL),
            ReportColumn("is_payment_blocked", "Оплаты закрыты", ColumnKind.BOOL),
            ReportColumn("balance", "Баланс", ColumnKind.MONEY, personal=True),
            ReportColumn(
                "pre_publication_expires_at", "Подписка до", ColumnKind.DATETIME
            ),
            ReportColumn("ads_count", "Объявлений", ColumnKind.INT),
            ReportColumn("published_count", "Опубликовано", ColumnKind.INT),
            ReportColumn("paid_total", "Оплатил всего", ColumnKind.MONEY),
            ReportColumn("spent_total", "Потратил с баланса", ColumnKind.MONEY),
        ),
    ),
    ReportSection.ADS: SectionDef(
        "Объявления",
        (
            ReportColumn("id", "ID", ColumnKind.INT),
            ReportColumn("created_at", "Создано", ColumnKind.DATETIME),
            _REGION,
            _USER_ID,
            _TG_ID,
            ReportColumn("ad_type", "Тип", transform=_label(AD_TYPE_LABELS)),
            ReportColumn("status", "Статус", transform=_label(AD_STATUS_LABELS)),
            ReportColumn("title", "Номер / магазин"),
            ReportColumn("city", "Город"),
            ReportColumn("price", "Цена", ColumnKind.INT),
            ReportColumn(
                "store_items",
                "Позиций в магазине",
                ColumnKind.INT,
                transform=lambda v: len(v) if isinstance(v, list) else None,
            ),
            ReportColumn("contact_username", "Контакт: username", personal=True),
            ReportColumn("contact_phone", "Контакт: телефон", personal=True),
            ReportColumn("publications_count", "Публикаций", ColumnKind.INT),
        ),
    ),
    ReportSection.PUBLICATIONS: SectionDef(
        "Публикации",
        (
            ReportColumn("id", "ID", ColumnKind.INT),
            ReportColumn("ad_id", "ID объявления", ColumnKind.INT),
            _REGION,
            _USER_ID,
            _TG_ID,
            ReportColumn("ad_type", "Тип", transform=_label(AD_TYPE_LABELS)),
            ReportColumn("title", "Номер / магазин"),
            ReportColumn(
                "status", "Статус", transform=_label(PUBLICATION_STATUS_LABELS)
            ),
            ReportColumn("slot_day", "День слота (местн.)", ColumnKind.DATE),
            ReportColumn(
                "slot_time",
                "Время слота (местн.)",
                transform=lambda t: t.strftime("%H:%M") if t else None,
            ),
            ReportColumn("publish_at_utc", "Выход по плану", ColumnKind.DATETIME),
            ReportColumn("published_at_utc", "Вышла", ColumnKind.DATETIME),
            ReportColumn("is_child", "Автоповтор", ColumnKind.BOOL),
            ReportColumn("services_count", "Услуг", ColumnKind.INT),
        ),
    ),
    ReportSection.SERVICES: SectionDef(
        "Услуги",
        (
            ReportColumn("id", "ID", ColumnKind.INT),
            ReportColumn("created_at", "Подключена", ColumnKind.DATETIME),
            _REGION,
            ReportColumn("publication_id", "ID публикации", ColumnKind.INT),
            ReportColumn("title", "Номер / магазин"),
            _USER_ID,
            _TG_ID,
            ReportColumn("type", "Услуга", transform=_label(SERVICE_TYPE_LABELS)),
            ReportColumn("status", "Статус", transform=_label(SERVICE_STATUS_LABELS)),
            ReportColumn("price_paid", "Цена", ColumnKind.MONEY),
        ),
    ),
}
