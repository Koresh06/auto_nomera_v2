from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.publication import PublicationStatus
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.services.slots.slot_reservation_service import SlotReservationService, HoldResult
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, eq=False)
class SelectSlotForPublicationRequest(UseCaseRequest):
    publication_id: int
    slot: SlotKey

    user_id: int        # кто выбрал
    ad_id: int          # объявление (у тебя это id Ad)
    now_utc: datetime | None = None

    # если ты хочешь поддержать сценарий "оплата уже подтверждена"
    payment_confirmed: bool = False


@dataclass(kw_only=True)
class SelectSlotForPublicationUseCase(UseCase[SelectSlotForPublicationRequest, HoldResult]):
    publication_repo: PublicationRepository
    region_repo: RegionRepository
    scheduler: Scheduler

    calendar_builder: CalendarBuilder
    time_resolver: PublishTimeResolver

    reservation_service: SlotReservationService
    pricing_policy: SlotPricingPolicy

    async def __call__(self, command: SelectSlotForPublicationRequest) -> HoldResult:
        now = command.now_utc or datetime.now(timezone.utc)

        publication = await self.publication_repo.get_by_id(command.publication_id)
        region = await self.region_repo.get_by_id(publication.region_id)

        # 1) Согласованный порядок слотов (как в UI)
        ordered_future_slots = self.calendar_builder.generate_future_slots(region=region, now_utc=now)

        # 2) HOLD слота (чтобы не выбрали двое)
        hold_result = await self.reservation_service.hold_slot(
            slot=command.slot,
            user_id=command.user_id,
            ad_id=command.ad_id,
            ordered_future_slots=ordered_future_slots,
            now_utc=now,
        )

        # 3) Вычисляем publish_at_utc
        publish_at_utc = self.time_resolver.resolve_publish_at_utc(region=region, slot=command.slot)

        # 4) Определяем "платный ли слот"
        # system paid = первые N
        is_system_paid = self.pricing_policy.is_system_paid(
            ordered_future_slots=ordered_future_slots,
            slot=command.slot,
        )

        # converted paid = либо уже был, либо стал сейчас (pricing_changed_to_converted=True)
        # (в реале converted_repo знает точно, но тут нам достаточно флага + system)
        is_paid_slot = is_system_paid or hold_result.pricing_changed_to_converted

        # 5) Если платный и оплаты нет — ставим ожидание оплаты (в scheduler НЕ ставим)
        if is_paid_slot and not command.payment_confirmed:
            publication.set_slot_pending_payment(slot=command.slot, publish_at_utc=publish_at_utc)
            await self.publication_repo.save(publication)
            return hold_result

        # 6) Иначе — сразу ставим в scheduler
        publication.schedule(slot=command.slot, publish_at_utc=publish_at_utc)
        await self.publication_repo.save(publication)

        await self.scheduler.schedule_publication(publication_id=publication.id, run_at_utc=publish_at_utc)
        return hold_result
