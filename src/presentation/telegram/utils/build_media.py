from aiogram.enums import ContentType
from aiogram_dialog.api.entities import MediaAttachment, MediaId


def build_media_attachment(image_file_id: str | None) -> MediaAttachment | None:
    if not image_file_id:
        return None
    if image_file_id.startswith("my://"):
        return MediaAttachment(type=ContentType.PHOTO, url=image_file_id)
    return MediaAttachment(
        type=ContentType.PHOTO,
        file_id=MediaId(file_id=image_file_id),
    )
