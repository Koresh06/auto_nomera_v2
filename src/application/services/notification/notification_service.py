from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class NotificationButton:
    text: str
    callback_data: str


@dataclass  
class NotificationMarkup:
    buttons: list[list[NotificationButton]]
    

class NotificationService(Protocol):
    async def notify_admins(
        self,
        *,
        text: str,
        photo_id: str | None = None,
        reply_markup: Any | None = None,
    ) -> None: ...


    async def notify_users(
        self,
        *,
        user_ids: list[int],
        text: str,
        reply_markup: Any | None = None,
    ) -> None: ...
    
    
    async def notify_user(
        self,
        *,
        tg_id: int,
        text: str,
        reply_markup: Any | None = None,
    ) -> None: ...

    async def broadcast_copy(
        self,
        *,
        chat_ids: list[int],
        from_chat_id: int,
        message_id: int,
        throttle_seconds: float = 0.05,
    ) -> dict:
        ...

    