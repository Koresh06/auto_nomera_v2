from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.application.dtos.schedule_stats import (
    RegionScheduleDTO,
    ScheduleDayDTO,
    ScheduleSlotDTO,
)
from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class GetRegionScheduleRequest(UseCaseRequest):
    region_id: int


@dataclass(kw_only=True)
class GetRegionScheduleUseCase(UseCase[GetRegionScheduleRequest, RegionScheduleDTO]):
    publication_repo: PublicationRepository
    region_repo: RegionRepository

    async def __call__(self, command: GetRegionScheduleRequest) -> RegionScheduleDTO:
        region = await self.region_repo.get_by_id(command.region_id)
        if region is None:
            raise RegionNotFoundException(command.region_id)

        days_range = region.settings.days_range
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        to_utc = today + timedelta(days=days_range)

        rows = await self.publication_repo.list_scheduled_by_region(
            command.region_id, today, to_utc
        )

        by_date: dict[str, list[ScheduleSlotDTO]] = {}
        for pub, plate, ad_type, username, tg_id in rows:
            if pub.publish_at_utc is None:
                continue
            date_key = pub.publish_at_utc.strftime("%d.%m.%Y")
            time_str = pub.publish_at_utc.strftime("%H:%M")
            by_date.setdefault(date_key, []).append(
                ScheduleSlotDTO(
                    publication_id=pub.id,
                    time=time_str,
                    plate=plate or "—",
                    ad_type=ad_type,
                    status=pub.status,
                    owner_tg_id=tg_id,
                    owner_username=username,
                )
            )

        days: list[ScheduleDayDTO] = []
        for i in range(days_range):
            d = today + timedelta(days=i)
            date_key = d.strftime("%d.%m.%Y")
            slots = sorted(by_date.get(date_key, []), key=lambda s: s.time)
            days.append(ScheduleDayDTO(date=date_key, slots=slots))

        return RegionScheduleDTO(
            region_title=region.title,
            days=days,
        )
