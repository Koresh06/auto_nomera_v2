
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.region import Region
from src.domain.enums.ad import AdType
from src.domain.services.publication.limiter import FREE_LIMITS, INTERVAL, LimitCheckResult
from src.domain.services.region.region_guard import RegionGuard


@dataclass(frozen=True, eq=False)
class CheckPublicationLimitRequest(UseCaseRequest):
    user_id: int
    region_id: int
    ad_type: AdType
    plate: str | None  # None для магазина
    publish_at_utc: datetime
    region_timezone: str


@dataclass(kw_only=True)
class CheckPublicationLimitUseCase(UseCase[CheckPublicationLimitRequest, LimitCheckResult]):
    region_guard: RegionGuard
    publication_repo: PublicationRepository
    ad_repo: AdRepository
    region_repo: RegionRepository

    async def __call__(self, command: CheckPublicationLimitRequest) -> LimitCheckResult:
        await self.region_guard.ensure_active(command.region_id)
        region: Region | None = await self.region_repo.get_by_id(command.region_id)
        if region is None:
            raise RegionNotFoundException(command.region_id)
        
        if region.settings and not region.settings.publication_limit_enabled:
            return LimitCheckResult.ok()

        window_start = command.publish_at_utc - INTERVAL
        limit = FREE_LIMITS.get(command.ad_type, 5)

        # 1) лимит по типу за 7 дней
        count = await self.publication_repo.count_scheduled_by_user(
            user_id=command.user_id,
            region_id=command.region_id,
            ad_type=command.ad_type,
            from_utc=window_start,
        )

        if count >= limit:
            return LimitCheckResult.denied(
                f"⛔ Достигнут лимит {limit} публикаций за 7 дней.\n\n"
                "Выберите 💰 платный слот или подождите."
            )

        # 2) интервал для конкретного номера (не для магазина)
        if command.plate and command.ad_type != AdType.STORE:
            last = await self.publication_repo.find_last_by_plate(
                user_id=command.user_id,
                region_id=command.region_id,
                plate=command.plate,
                from_utc=window_start,
            )
            if last and last.publish_at_utc:
                next_free = last.publish_at_utc + INTERVAL
                if command.publish_at_utc < next_free:
                    tz = ZoneInfo(command.region_timezone)
                    next_local = next_free.astimezone(tz)
                    return LimitCheckResult.denied(
                        f"⛔ Этот номер публиковался недавно.\n\n"
                        f"📅 Следующее бесплатное окно:\n"
                        f"{next_local:%d.%m.%Y %H:%M}\n\n"
                        "Выберите 💰 платный слот или подождите."
                    )

        return LimitCheckResult.ok()