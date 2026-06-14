from typing import Protocol
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublishResult:
    channel_id: int
    message_id: int


class TelegramPublisher(Protocol):
    
    async def publish_photo(
        self,
        *,
        channel_id: int,
        image_file_id: str,
        caption: str,
    ) -> PublishResult: ...

    async def publish_text(
        self,
        *,
        channel_id: int,
        text: str,
    ) -> PublishResult: ...

    async def edit_caption(
        self,
        *,
        channel_id: int,
        message_id: int,
        caption: str,
    ) -> None: ...

    async def pin_message(
        self,
        *,
        channel_id: int,
        message_id: int,
    ) -> None: ...

    async def unpin_message(
        self,
        *,
        channel_id: int,
        message_id: int,
    ) -> None: ...

    async def edit_media(
        self,
        *,
        channel_id: int,
        message_id: int,
        file_id: str,
        caption: str,
    ) -> None: ...
