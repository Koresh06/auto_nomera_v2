from datetime import timedelta
from aiogram import Bot
from dishka import Provider, Scope, provide

from src.application.ports.region.region_repo import RegionRepository
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.ports.publication_service.image_processor import ImageProcessor
from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.application.services.payment.provider_registry import PaymentProviderRegistry
from src.core.config import AppSettings
from src.domain.enums.payment import PaymentMethod
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.region.region_guard import RegionGuard
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.infrastructure.payment.providers.cryptomus import CryptomusProvider
from src.infrastructure.payment.providers.manual_card import ManualCardProvider
from src.infrastructure.payment.providers.telegram_stars import TelegramStarsProvider
from src.infrastructure.payment.providers.yookassa import YooKassaProvider
from src.infrastructure.telegram.image_processor import PillowImageProcessor
from src.infrastructure.telegram.notification_service import AiogramNotificationService


class ServicesProvider(Provider):

    @provide(scope=Scope.APP)
    def slot_hold_ttl(self, settings: AppSettings) -> timedelta:
        return timedelta(seconds=settings.app.hold_slots_time)

    @provide(scope=Scope.APP)
    def calendar_builder(self) -> CalendarBuilder:
        return CalendarBuilder()

    @provide(scope=Scope.APP)
    def slot_pricing_policy(self) -> SlotPricingPolicy:
        return SlotPricingPolicy(system_paid_count=3)

    @provide(scope=Scope.APP)
    def publish_time_resolver(self) -> PublishTimeResolver:
        return PublishTimeResolver()

    @provide(scope=Scope.APP)
    def renderer(self, settings: AppSettings) -> AdTextRenderer:
        return AdTextRenderer(
            settings.telegram.bot_url,
            settings.telegram.buyout_url,
        )

    @provide(scope=Scope.REQUEST)
    def slot_reservation_service(
        self,
        booking_repo: SlotBookingRepository,
        converted_repo: SlotConvertedRepository,
        hold_store: SlotHoldStore,
        pricing_policy: SlotPricingPolicy,
        slot_hold_ttl: timedelta,
    ) -> SlotReservationService:
        return SlotReservationService(
            booking_repo=booking_repo,
            converted_repo=converted_repo,
            hold_store=hold_store,
            pricing_policy=pricing_policy,
            hold_ttl=slot_hold_ttl,
        )

    @provide(scope=Scope.REQUEST)
    def image_processor(self, bot: Bot) -> ImageProcessor:
        return PillowImageProcessor(bot)

    @provide(scope=Scope.APP)
    def notification_service(
        self,
        bot: Bot,
        settings: AppSettings,
    ) -> NotificationService:
        return AiogramNotificationService(
            bot=bot,
            admin_ids=settings.telegram.admin_ids,
        )

    @provide(scope=Scope.APP)
    def payment_provider_registry(
        self,
        bot: Bot,
        settings: AppSettings,
    ) -> PaymentProviderRegistry:
        registry = PaymentProviderRegistry()
        registry.register(
            PaymentMethod.TELEGRAM_STARS,
            TelegramStarsProvider(
                bot=bot, xtr_to_rub_rate=settings.payment.telegram_stars.xtr_to_rub_rate
            ),
        )
        registry.register(
            PaymentMethod.MANUAL_CARD,
            ManualCardProvider(card=settings.payment.manual_card.card_number),
        )
        registry.register(
            PaymentMethod.YOOKASSA,
            YooKassaProvider(
                account_id=settings.payment.yookassa.account_id,
                secret_key=settings.payment.yookassa.secret_key,
                settings=settings.payment.yookassa,
            ),
        )
        registry.register(PaymentMethod.CRYPTO, CryptomusProvider())
        return registry

    @provide(scope=Scope.REQUEST)
    def region_guard(self, region_repo: RegionRepository) -> RegionGuard:
        return RegionGuard(region_repo)