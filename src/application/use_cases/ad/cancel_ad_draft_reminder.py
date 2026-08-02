from dataclasses import dataclass

from src.application.ports.ad.draft_reminder_store import DraftReminderStore
from src.application.ports.tasks.task_queue import TaskQueue
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class CancelAdDraftReminderRequest(UseCaseRequest):
    user_id: int


@dataclass(kw_only=True)
class CancelAdDraftReminderUseCase(UseCase[CancelAdDraftReminderRequest, None]):
    task_queue: TaskQueue
    reminder_store: DraftReminderStore

    async def __call__(self, command: CancelAdDraftReminderRequest) -> None:
        job_id = await self.reminder_store.get_job_id(user_id=command.user_id)
        if job_id is None:
            return
        await self.task_queue.cancel(job_id=job_id)
        await self.reminder_store.delete(user_id=command.user_id)
