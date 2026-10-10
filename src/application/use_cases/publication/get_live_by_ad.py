from dataclasses import dataclass

from src.application.dtos.publication import PublicationDTO
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.publication import PublicationStatus


@dataclass(frozen=True, eq=False)
class GetLivePublicationOfAdRequest(UseCaseRequest):
    ad_id: int


@dataclass(kw_only=True)
class GetLivePublicationOfAdUseCase(
    UseCase[GetLivePublicationOfAdRequest, PublicationDTO | None]
):
    """Публикация, чей пост сейчас висит в канале: последняя PUBLISHED с
    message_id. В «Моих объявлениях» у объявления открывается самая новая
    публикация — при автопубликации или повторном размещении это
    запланированная копия, а не опубликованный пост, и правка уходила только
    в БД."""

    publication_repo: PublicationRepository

    async def __call__(
        self, command: GetLivePublicationOfAdRequest
    ) -> PublicationDTO | None:
        pubs = await self.publication_repo.list_scheduled_by_ad(command.ad_id)
        live = [
            p
            for p in pubs
            if p.status == PublicationStatus.PUBLISHED
            and p.channel_message_id is not None
        ]
        if not live:
            return None
        latest = max(
            live,
            key=lambda p: (p.published_at_utc is not None, p.published_at_utc, p.id),
        )
        return PublicationDTO.from_entity(latest)
