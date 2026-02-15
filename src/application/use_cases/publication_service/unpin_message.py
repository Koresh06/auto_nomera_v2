from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.ports.publication_service.telegram_publisher import TelegramPublisher
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class UnpinMessageRequest(UseCaseRequest):
    channel_id: int
    message_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class UnpinMessageUseCase(UseCase[UnpinMessageRequest, None]):
    telegram: TelegramPublisher

    async def __call__(self, command: UnpinMessageRequest) -> None:
        _ = command.now_utc or datetime.now(timezone.utc)
        await self.telegram.unpin_message(channel_id=command.channel_id, message_id=command.message_id)
