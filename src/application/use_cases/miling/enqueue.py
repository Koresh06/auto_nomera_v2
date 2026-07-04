import logging
from dataclasses import dataclass

from src.application.ports.tasks.task_queue import TaskQueue
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.miling import MailingType

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class EnqueueMailingRequest(UseCaseRequest):
    mail_type: MailingType
    from_chat_id: int
    message_id: int
    region_id: int | None = None


@dataclass(kw_only=True)
class EnqueueMailingUseCase(UseCase[EnqueueMailingRequest, None]):
    task_queue: TaskQueue

    async def __call__(self, command: EnqueueMailingRequest) -> None:
        await self.task_queue.enqueue(
            task_name="execute_mailing",
            args=(
                command.mail_type.value,
                command.from_chat_id,
                command.message_id,
                command.region_id,
            ),
        )
        logger.info(
            "[EnqueueMailing] type=%s region_id=%s",
            command.mail_type,
            command.region_id,
        )
