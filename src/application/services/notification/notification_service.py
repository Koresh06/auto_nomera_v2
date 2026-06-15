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