from typing import Protocol


class TelegramPublisher(Protocol):
    async def send_ad(
        self,
        *,
        channel_id: int,
        text: str,
        image_file_id: str | None,
    ) -> int:
        """Возвращает message_id опубликованного сообщения."""
        ...

    async def pin_message(self, *, channel_id: int, message_id: int) -> None:
        ...

    async def unpin_message(self, *, channel_id: int, message_id: int) -> None:
        ...
