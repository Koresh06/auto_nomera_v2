"""
Tests for the priority-publish scheduling fixes:

- AUD-02: schedule_publish_now() used to be a bare queue.enqueue() with no
  scheduler_job_id persisted — a publication "published now" stayed SCHEDULED
  with scheduler_job_id=None forever if the stream message was lost, invisible
  to every recovery tool (restore_schedule.py etc). It now goes through the
  same durable schedule_publication() path.
- AUD-09: TaskQueue.cancel() failing must not be treated as success —
  cancel_publication() used to always clear scheduler_job_id regardless,
  risking the old job firing *and* the new one (duplicate post).
- AUD-13: the SCHEDULED branch of PriorityPublishPublicationUseCase never
  called service.mark_used(), unlike the PUBLISHED branch.
"""

from datetime import datetime

import pytest

from src.application.use_cases.publication_service.priority_publish_publication import (
    PriorityPublishPublicationRequest,
    PriorityPublishPublicationUseCase,
)
from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.exceptions.publication import SchedulerCancellationFailed
from src.infrastructure.scheduler.taskiq_queue_scheduler import TaskQueueScheduler


class FakePublicationRepo:
    def __init__(self, pub: Publication) -> None:
        self._store: dict[int, Publication] = {pub.id: pub}
        self.created: list[Publication] = []

    async def get_by_id(self, publication_id: int) -> Publication | None:
        return self._store.get(publication_id)

    async def save(self, publication: Publication) -> None:
        self._store[publication.id] = publication

    async def create(self, publication: Publication) -> Publication:
        publication.id = len(self._store) + 100
        self._store[publication.id] = publication
        self.created.append(publication)
        return publication


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass


class FakeTaskQueue:
    def __init__(self, *, cancel_succeeds: bool = True) -> None:
        self.scheduled: list[tuple[str, tuple, datetime]] = []
        self.cancel_calls: list[str] = []
        self._cancel_succeeds = cancel_succeeds

    async def enqueue(self, *, task_name: str, args: tuple) -> str | None:
        return "enqueued-job"

    async def schedule(self, *, task_name: str, args: tuple, run_at_utc) -> str | None:
        job_id = f"job-{len(self.scheduled)}"
        self.scheduled.append((task_name, args, run_at_utc))
        return job_id

    async def cancel(self, *, job_id: str) -> bool:
        self.cancel_calls.append(job_id)
        return self._cancel_succeeds


def make_publication(**overrides) -> Publication:
    defaults = dict(
        id=1,
        ad_id=10,
        region_id=1,
        status=PublicationStatus.SCHEDULED,
        scheduler_job_id="old-job-id",
    )
    defaults.update(overrides)
    return Publication(**defaults)


async def test_schedule_publish_now_sets_scheduler_job_id():
    """AUD-02: publish-now must leave the publication with a real
    scheduler_job_id, discoverable by recovery tooling."""
    pub = make_publication(scheduler_job_id=None)
    repo = FakePublicationRepo(pub)
    tx = FakeTransactionManager()
    queue = FakeTaskQueue()
    scheduler = TaskQueueScheduler(
        queue=queue, publication_repo=repo, transaction_manager=tx
    )

    await scheduler.schedule_publish_now(publication_id=pub.id)

    stored = await repo.get_by_id(pub.id)
    assert stored.scheduler_job_id is not None
    # schedule() (durable) was used, not a bare enqueue()
    assert len(queue.scheduled) == 1
    assert queue.scheduled[0][0] == "publish_publication"
    assert tx.commits == 1


async def test_cancel_publication_clears_job_id_on_success():
    pub = make_publication(scheduler_job_id="old-job-id")
    repo = FakePublicationRepo(pub)
    tx = FakeTransactionManager()
    queue = FakeTaskQueue(cancel_succeeds=True)
    scheduler = TaskQueueScheduler(
        queue=queue, publication_repo=repo, transaction_manager=tx
    )

    await scheduler.cancel_publication(publication_id=pub.id)

    stored = await repo.get_by_id(pub.id)
    assert stored.scheduler_job_id is None
    assert tx.commits == 1


async def test_cancel_publication_raises_and_keeps_job_id_on_failure():
    """AUD-09: a failed cancel must not be treated as if the old job is gone —
    otherwise a caller might schedule a second job and get a duplicate post."""
    pub = make_publication(scheduler_job_id="old-job-id")
    repo = FakePublicationRepo(pub)
    tx = FakeTransactionManager()
    queue = FakeTaskQueue(cancel_succeeds=False)
    scheduler = TaskQueueScheduler(
        queue=queue, publication_repo=repo, transaction_manager=tx
    )

    with pytest.raises(SchedulerCancellationFailed):
        await scheduler.cancel_publication(publication_id=pub.id)

    stored = await repo.get_by_id(pub.id)
    assert stored.scheduler_job_id == "old-job-id"  # not cleared
    assert tx.commits == 0  # not committed as if it succeeded


async def test_priority_publish_scheduled_branch_marks_service_used():
    """AUD-13: previously only the PUBLISHED branch called mark_used()."""
    pub = make_publication(status=PublicationStatus.SCHEDULED)
    service = PublicationService(
        id=1,
        type=PublicationServiceType.PRIORITY_PUBLISH,
        status=PublicationServiceStatus.ACTIVE,
    )
    pub.services.append(service)

    repo = FakePublicationRepo(pub)
    tx = FakeTransactionManager()
    queue = FakeTaskQueue()
    scheduler = TaskQueueScheduler(
        queue=queue, publication_repo=repo, transaction_manager=tx
    )

    use_case = PriorityPublishPublicationUseCase(
        publication_repo=repo, scheduler=scheduler, transaction_manager=tx
    )

    await use_case(PriorityPublishPublicationRequest(publication_id=pub.id))

    assert service.status == PublicationServiceStatus.USED


async def test_priority_publish_published_branch_still_marks_service_used():
    """Regression guard for the branch that already worked correctly."""
    pub = make_publication(status=PublicationStatus.PUBLISHED, scheduler_job_id=None)
    service = PublicationService(
        id=1,
        type=PublicationServiceType.PRIORITY_PUBLISH,
        status=PublicationServiceStatus.ACTIVE,
    )
    pub.services.append(service)

    repo = FakePublicationRepo(pub)
    tx = FakeTransactionManager()
    queue = FakeTaskQueue()
    scheduler = TaskQueueScheduler(
        queue=queue, publication_repo=repo, transaction_manager=tx
    )

    use_case = PriorityPublishPublicationUseCase(
        publication_repo=repo, scheduler=scheduler, transaction_manager=tx
    )

    await use_case(PriorityPublishPublicationRequest(publication_id=pub.id))

    assert service.status == PublicationServiceStatus.USED
    assert len(repo.created) == 1  # child publication created
    child = repo.created[0]
    assert child.is_child is True
    assert child.scheduler_job_id is not None  # AUD-02 applies here too
