from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.services.slots.slot_reservation_service import (
    SlotReservationService,
    HoldResult,
)
from src.domain.value_objects.slot_key import SlotKey
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.use_cases.base import UseCase, UseCaseRequest


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class SelectSlotForPublicationRequest(UseCaseRequest):
    publication_id: int
    slot: SlotKey

    user_id: int  # кто выбрал
    ad_id: int  # объявление (у тебя это id Ad)
    now_utc: datetime | None = None

    # если ты хочешь поддержать сценарий "оплата уже подтверждена"
    payment_confirmed: bool = False


@dataclass(kw_only=True)
class SelectSlotForPublicationUseCase(UseCase[SelectSlotForPublicationRequest, None]):
    publication_repo: PublicationRepository
    region_repo: RegionRepository
    scheduler: Scheduler
    calendar_builder: CalendarBuilder
    time_resolver: PublishTimeResolver
    reservation_service: SlotReservationService
    pricing_policy: SlotPricingPolicy

    async def __call__(self, command: SelectSlotForPublicationRequest) -> None:
        now = command.now_utc or datetime.now(timezone.utc)

        logger.info(
            f"[SelectSlot] pub_id={command.publication_id} "
            f"slot={command.slot.local_day} {command.slot.local_time} "
            f"user_id={command.user_id} ad_id={command.ad_id}"
        )

        publication = await self.publication_repo.get_by_id(command.publication_id)
        region = await self.region_repo.get_by_id(publication.region_id)
        logger.info(f"[SelectSlot] region={region.title!r} tz={region.timezone.value!r}")

        ordered_future_slots = self.calendar_builder.generate_future_slots(
            region=region,
            now_utc=now,
        )

        publish_at_utc = self.time_resolver.resolve_publish_at_utc(
            tz=region.timezone,
            slot=command.slot,
        )
        logger.info(f"[SelectSlot] publish_at_utc={publish_at_utc.isoformat()}")

        is_system_paid = self.pricing_policy.is_system_paid(
            ordered_future_slots=ordered_future_slots,
            slot=command.slot,
        )

        # ← проверяем converted через репо, не через hold_result
        is_converted = await self.reservation_service.converted_repo.is_converted(
            command.slot
        )

        is_paid_slot = is_system_paid or is_converted
        logger.info(
            f"[SelectSlot:pricing] is_system_paid={is_system_paid} "
            f"is_converted={is_converted} is_paid_slot={is_paid_slot} "
            f"payment_confirmed={command.payment_confirmed}"
        )

        if is_paid_slot and not command.payment_confirmed:
            publication.set_slot_pending_payment(
                slot=command.slot, publish_at_utc=publish_at_utc
            )
            await self.publication_repo.save(publication)
            logger.info(f"[SelectSlot:awaiting_payment] pub_id={publication.id}")
            return

        publication.schedule(slot=command.slot, publish_at_utc=publish_at_utc)
        await self.publication_repo.save(publication)

        await self.scheduler.schedule_publication(
            publication_id=publication.id,
            run_at_utc=publish_at_utc,
        )
        logger.info(
            f"[SelectSlot:done] pub_id={publication.id} status={publication.status}"
        )