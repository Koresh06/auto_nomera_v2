import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import ContentType
from aiogram_dialog.api.entities import MediaAttachment

from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.telegram.media_virtual_url import build_virtual_plate_url
from src.presentation.telegram.common.custom_message_manager import CustomMessageManager


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
    bot: Bot
    message_manager: CustomMessageManager
    async def __call__(
        self, command: EnsureAdImageRefRequest
    ) -> MediaAttachment | None:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            url=build_virtual_plate_url(
                plate_number=command.plate,
                channel_username=command.channel_username,
                chat_id=command.chat_id,
            ),
        )

        await self.message_manager.get_media_source(
            media,
            self.bot,
        )

        logger.info(f"[EnsureAdImageRef] plate={command.plate} image={media.url}")
        return media
