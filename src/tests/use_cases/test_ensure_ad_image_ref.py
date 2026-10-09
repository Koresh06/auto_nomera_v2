"""
Coverage for EnsureAdImageRefUseCase — previously skipped as "depends on a
real aiogram Bot", but message_manager.get_media_source is an injected
dependency we can fake like any other port, so it's testable after all.
"""

from aiogram.types import ContentType
from aiogram_dialog.api.entities import MediaAttachment

from src.application.use_cases.ad.ensure_ad_image_ref import (
    EnsureAdImageRefRequest,
    EnsureAdImageRefUseCase,
)
from src.infrastructure.telegram.media_virtual_url import build_virtual_plate_url


class FakeMessageManager:
    def __init__(self, file_id: str = "resolved-file-id") -> None:
        self.file_id = file_id
        self.calls: list[tuple[MediaAttachment, object]] = []

    async def get_media_source(self, media: MediaAttachment, bot) -> str:
        self.calls.append((media, bot))
        media.file_id = self.file_id
        return self.file_id


async def test_ensure_ad_image_ref_builds_virtual_url_and_resolves_file_id():
    message_manager = FakeMessageManager(file_id="file-123")
    bot = object()
    use_case = EnsureAdImageRefUseCase(bot=bot, message_manager=message_manager)

    result = await use_case(
        EnsureAdImageRefRequest(
            plate="А001АА77", channel_username="testchannel", chat_id=555
        )
    )

    assert result.type == ContentType.PHOTO
    assert result.url == build_virtual_plate_url(
        plate_number="А001АА77", channel_username="testchannel", chat_id=555
    )
    assert result.file_id == "file-123"
    assert len(message_manager.calls) == 1
    called_media, called_bot = message_manager.calls[0]
    assert called_media.url == result.url
    assert called_bot is bot
