import logging
from dataclasses import dataclass

from aiogram.types import ContentType
from aiogram_dialog.api.entities import MediaAttachment

from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.telegram.media_virtual_url import build_virtual_plate_url


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class EnsureAdImageRefRequest(UseCaseRequest):
    plate: str
    channel_username: str
    chat_id: int


@dataclass(kw_only=True)
class EnsureAdImageRefUseCase(
    UseCase[
        EnsureAdImageRefRequest,
        MediaAttachment | None,
    ],
):
    async def __call__(
        self, command: EnsureAdImageRefRequest
    ) -> MediaAttachment | None:
        virtual_url = build_virtual_plate_url(
            plate_number=command.plate,
            channel_username=command.channel_username,
            chat_id=command.chat_id,
        )
        image = MediaAttachment(
            type=ContentType.PHOTO,
            url=virtual_url,
        )
        logger.info(f"[EnsureAdImageRef] plate={command.plate} image={image.url}")

        return image
