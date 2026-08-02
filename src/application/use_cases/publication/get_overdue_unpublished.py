from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.ad import AdType


@dataclass(frozen=True)
class OverdueAdItemDTO:
    publication_id: int
    plate_number: str
    ad_type: AdType
    owner_username: str | None
    owner_tg_id: int
    local_time_label: str

    @property
    def ad_type_display(self) -> str:
        return self.ad_type.display

    @property
    def owner_link(self) -> str:
        if self.owner_username:
            return f'<a href="https://t.me/{self.owner_username}">👤</a>'
        return f'<a href="tg://user?id={self.owner_tg_id}">👤</a>'


@dataclass(frozen=True, eq=False)
class GetOverdueUnpublishedRequest(UseCaseRequest):
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class GetOverdueUnpublishedUseCase(
    UseCase[GetOverdueUnpublishedRequest, list[OverdueAdItemDTO]]
):
    publication_repo: PublicationRepository

    async def __call__(
        self, command: GetOverdueUnpublishedRequest
    ) -> list[OverdueAdItemDTO]:
        now = command.now_utc or datetime.now(timezone.utc)
        rows = await self.publication_repo.list_overdue_scheduled_today(now_utc=now)

        items: list[OverdueAdItemDTO] = []
        for pub, plate, ad_type, username, tg_id, shop_name, tz_name in rows:
            display_plate = shop_name if ad_type == AdType.STORE else plate

            slot_label = pub.slot.local_time.strftime("%H:%M") if pub.slot else "—"

            items.append(
                OverdueAdItemDTO(
                    publication_id=pub.id,
                    plate_number=display_plate or "-",
                    ad_type=ad_type,
                    owner_username=username,
                    owner_tg_id=tg_id,
                    local_time_label=slot_label,
                )
            )
        return items
