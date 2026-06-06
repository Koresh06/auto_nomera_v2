from datetime import timedelta
from aiogram import Bot
from dishka import Provider, Scope, provide

from src.core.config import settings
from src.application.ports.publication_service.image_processor import ImageProcessor
from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.infrastructure.telegram.image_processor import PillowImageProcessor


class ServicesProvider(Provider):

    @provide(scope=Scope.APP)
    def slot_hold_ttl(self) -> timedelta:
        return timedelta(seconds=30)

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
    def renderer(self) -> AdTextRenderer:
        return AdTextRenderer(settings.telegram.bot_url)

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
