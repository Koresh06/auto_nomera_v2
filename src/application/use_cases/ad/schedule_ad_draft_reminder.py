from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.application.ports.ad.draft_reminder_store import DraftReminderStore
from src.application.ports.tasks.task_queue import TaskQueue
from src.application.use_cases.base import UseCase, UseCaseRequest

REMINDER_DELAY_HOURS = 2
REMINDER_TTL_SECONDS = REMINDER_DELAY_HOURS * 3600 + 300  # небольшой запас


@dataclass(frozen=True, eq=False)
class ScheduleAdDraftReminderRequest(UseCaseRequest):
    user_id: int
    tg_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class ScheduleAdDraftReminderUseCase(UseCase[ScheduleAdDraftReminderRequest, None]):
    task_queue: TaskQueue
    reminder_store: DraftReminderStore

    async def __call__(self, command: ScheduleAdDraftReminderRequest) -> None:
        now = command.now_utc or datetime.now(timezone.utc)
        run_at = now + timedelta(hours=REMINDER_DELAY_HOURS)

        # если уже есть активное напоминание для этого юзера — сначала снимаем,
        # чтобы не плодить дубли при повторном входе в диалог
        existing_job_id = await self.reminder_store.get_job_id(user_id=command.user_id)
        if existing_job_id:
            await self.task_queue.cancel(job_id=existing_job_id)

        job_id = await self.task_queue.schedule(
            task_name="send_ad_draft_reminder",
            args=(command.tg_id,),
            run_at_utc=run_at,
        )
        if job_id:
            await self.reminder_store.set_job_id(
                user_id=command.user_id,
                job_id=job_id,
                ttl_seconds=REMINDER_TTL_SECONDS,
            )
