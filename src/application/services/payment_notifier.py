from datetime import datetime
from zoneinfo import ZoneInfo

from src.domain.entities.payment import Payment, PaymentPurpose
from src.domain.entities.user import User
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.ports.region.region_repo import RegionRepository

_MSK = ZoneInfo("Europe/Moscow")


class PaymentNotifier:
    def __init__(
        self,
        notification_service: NotificationService,
        region_repo: RegionRepository,
    ) -> None:
        self._notifier = notification_service
        self._region_repo = region_repo

    async def notify_user(self, payment: Payment, extra: dict | None = None) -> None:
        return_to = payment.meta.get("return_to")
        if not return_to:
            return
        text = self._build_user_text(payment, extra)
        try:
            await self._notifier.notify_user(tg_id=return_to["user_id"], text=text)
        except Exception:
            pass

    @staticmethod
    def _build_user_text(payment: Payment, extra: dict | None = None) -> str:
        extra = extra or {}
        header = "🎉 <b>Оплата прошла успешно!</b>"

        match payment.purpose:
            case PaymentPurpose.BALANCE_TOPUP:
                body = f"✨ Баланс пополнен на <b>{payment.amount} ₽</b>"
            case PaymentPurpose.PUBLICATION_SERVICE:
                title = extra.get("title", "Услуга")
                body = f"<b>{title}</b>\nУслуга подключена и применена к объявлению"
            case PaymentPurpose.PRE_PUBLICATION:
                days = extra.get("days", 30)
                action = "продлена" if extra.get("was_active") else "активирована"
                body = f"💎 Подписка на ранний доступ <b>{action}</b>\nна {days} дн."
            case PaymentPurpose.SLOT:
                slot_text = extra.get("slot_text", "")
                suffix = f"\n🕒 {slot_text}" if slot_text else ""
                body = f"📅 Слот <b>оплачен и забронирован</b>!{suffix}"
            case _:
                body = "✅ Платёж подтверждён"

        return f"{header}\n\n{body}"

    async def notify_admins(self, payment: Payment, user: User) -> None:
        try:
            text = await self._build_admin_text(payment, user)
            await self._notifier.notify_admins(text=text)
        except Exception:
            pass

    async def _build_admin_text(self, payment: Payment, user: User) -> str:
        region_title = await self._region_title(user)
        time_str = self._msk_time(payment.paid_at)
        user_link = self._user_link(user)

        return (
            f"💸 <b>Успешная оплата</b>\n\n"
            f"👤 {user_link}\n"
            f"🆔 <code>{user.tg_id}</code>\n"
            f"🌍 Регион: {region_title}\n"
            f"━━━━━━━━━━━━━━\n"
            f"{self._purpose_line(payment.purpose)}\n"
            f"💰 Сумма: <b>{payment.amount:.0f} руб.</b>\n"
            f"💳 Способ: {payment.method_label}\n"
            f"🧾 <code>{payment.external_id}</code>\n"
            f"🕓 {time_str} (МСК)"
        )

    async def _region_title(self, user: User) -> str:
        if not user.region_id:
            return "—"
        region = await self._region_repo.get_by_id(user.region_id)
        return region.title if region else "—"

    @staticmethod
    def _msk_time(paid_at: datetime | None) -> str:
        return (
            paid_at.astimezone(_MSK).strftime("%d.%m.%Y %H:%M:%S") if paid_at else "—"
        )

    @staticmethod
    def _user_link(user: User) -> str:
        label = user.full_name or user.username or "профиль"
        if user.username:
            return f'<a href="https://t.me/{user.username}">{label}</a>'
        return f'<a href="tg://user?id={user.tg_id}">{label}</a>'

    @staticmethod
    def _purpose_line(purpose: PaymentPurpose) -> str:
        return {
            PaymentPurpose.BALANCE_TOPUP: "📥 <b>Пополнение баланса</b>",
            PaymentPurpose.PUBLICATION_SERVICE: "💎 <b>Платная услуга</b>",
            PaymentPurpose.PRE_PUBLICATION: "💎 <b>Подписка (до публикации)</b>",
            PaymentPurpose.SLOT: "📅 <b>Платный слот</b>",
        }.get(purpose, "🛒 <b>Покупка</b>")
