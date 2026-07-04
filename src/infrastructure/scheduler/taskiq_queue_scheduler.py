from datetime import datetime

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.tasks.task_queue import TaskQueue
from src.infrastructure.database.transaction_manager.base import TransactionManager


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
        if job_id:
            pub.set_scheduler_job(job_id)
            await self._publication_repo.save(pub)
            await self._transaction_manager.commit()

    async def cancel_publication(self, *, publication_id: int) -> None:
        pub = await self._publication_repo.get_by_id(publication_id)
        if pub is None:
            raise PublicationNotFoundException(publication_id)

        if not pub.scheduler_job_id:
            return
        await self._queue.cancel(job_id=pub.scheduler_job_id)
        pub.clear_scheduler_job()
        await self._publication_repo.save(pub)
        await self._transaction_manager.commit()

    async def schedule_publish_now(self, *, publication_id: int) -> None:
        await self._queue.enqueue(
            task_name="publish_publication", args=(publication_id,)
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
