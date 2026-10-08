import logging
from datetime import datetime, timedelta, timezone

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.tasks.task_queue import TaskQueue
from src.domain.exceptions.publication import SchedulerCancellationFailed
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


class TaskQueueScheduler(Scheduler):
    def __init__(
        self,
        *,
        queue: TaskQueue,
        publication_repo: PublicationRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._queue = queue
        self._publication_repo = publication_repo
        self._transaction_manager = transaction_manager

    async def schedule_publication(
        self,
        *,
        publication_id: int,
        run_at_utc: datetime,
    ) -> None:
        pub = await self._publication_repo.get_by_id(publication_id)
        if pub is None:
            raise PublicationNotFoundException(publication_id)

        job_id = await self._queue.schedule(
            task_name="publish_publication",
            args=(publication_id,),
            run_at_utc=run_at_utc,
        )
        if not job_id:
            # Задача в Redis, вероятно, уже создана (schedule() успел дойти
            # до постановки), но без job_id мы не можем привязать её к
            # публикации — SCHEDULED без scheduler_job_id нарушает инвариант
            # "любая SCHEDULED публикация обнаружима". Громко отказываемся,
            # а не тихо пропускаем сохранение/коммит.
            logger.error(
                f"[schedule_publication] queue.schedule() returned falsy job_id "
                f"for pub_id={publication_id}"
            )
            raise RuntimeError(
                f"TaskQueue.schedule() returned no job_id for publication {publication_id}"
            )
        pub.set_scheduler_job(job_id)
        await self._publication_repo.save(pub)
        await self._transaction_manager.commit()

    async def cancel_publication(self, *, publication_id: int) -> None:
        pub = await self._publication_repo.get_by_id(publication_id)
        if pub is None:
            raise PublicationNotFoundException(publication_id)

        if not pub.scheduler_job_id:
            return
        cancelled = await self._queue.cancel(job_id=pub.scheduler_job_id)
        if not cancelled:
            # Отмена не гарантирована — старая задача может ещё выстрелить.
            # НЕ очищаем scheduler_job_id и не коммитим, чтобы вызывающий код
            # не продолжил как будто слот/публикация свободны (иначе — дубль
            # публикации, если следом ставится новая немедленная задача).
            logger.error(
                f"[cancel_publication] failed to cancel job {pub.scheduler_job_id} "
                f"for pub_id={publication_id} — refusing to proceed"
            )
            raise SchedulerCancellationFailed(
                f"Could not cancel job {pub.scheduler_job_id} for publication {publication_id}"
            )
        pub.clear_scheduler_job()
        await self._publication_repo.save(pub)
        await self._transaction_manager.commit()

    async def schedule_publish_now(self, *, publication_id: int) -> None:
        # Раньше это был "голый" enqueue без scheduler_job_id — публикация
        # оставалась SCHEDULED без job_id и была невидима для всех
        # инструментов восстановления (restore_schedule.py и т.п.), если
        # сообщение в Redis Stream терялось. Теперь используем тот же durable
        # путь, что и обычное планирование, просто с ближайшим run_at_utc.
        await self.schedule_publication(
            publication_id=publication_id,
            run_at_utc=datetime.now(timezone.utc) + timedelta(seconds=2),
        )

    async def schedule_unpin(
        self,
        *,
        channel_id: int,
        message_id: int,
        run_at_utc: datetime,
    ) -> None:
        await self._queue.schedule(
            task_name="unpin_message",
            args=(channel_id, message_id),
            run_at_utc=run_at_utc,
        )
