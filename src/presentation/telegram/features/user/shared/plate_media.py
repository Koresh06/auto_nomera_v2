from aiogram_dialog.api.entities import MediaAttachment

from src.application.mediator import Mediator
from src.application.use_cases.ad.ensure_ad_image_ref import EnsureAdImageRefRequest
from src.presentation.telegram.utils.build_media import build_media_attachment


_CACHE_KEY = "generated_plate_media"


async def ensure_plate_media(
    dialog_data: dict,
    mediator: Mediator,
    *,
    plate: str,
    channel_username: str,
    chat_id: int,
) -> MediaAttachment | None:
    """Сгенерированная картинка номера, загружается в Telegram один раз.

    Раньше геттер окна подтверждения генерировал PNG и грузил его через
    временное сообщение на каждую перерисовку окна. При тормозах Telegram
    API каждая перерисовка висела до таймаута (60с) и падала с
    «Cannot get window data». file_id кешируется в dialog_data по паре
    (номер, канал): смена номера даёт новую картинку.
    """
    cached = dialog_data.get(_CACHE_KEY)
    if (
        cached
        and cached.get("plate") == plate
        and cached.get("channel_username") == channel_username
    ):
        return build_media_attachment(cached["file_id"])

    media: MediaAttachment | None = await mediator.handle(
        EnsureAdImageRefRequest(
            plate=plate,
            channel_username=channel_username,
            chat_id=chat_id,
        )
    )
    if media and media.file_id:
        dialog_data[_CACHE_KEY] = {
            "plate": plate,
            "channel_username": channel_username,
            "file_id": media.file_id.file_id,
        }
    return media
