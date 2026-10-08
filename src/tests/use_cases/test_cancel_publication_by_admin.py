from src.application.use_cases.publication.cancel_by_admin import (
    CancelPublicationByAdminRequest,
    CancelPublicationByAdminUseCase,
)
from src.domain.entities.publication import Publication
from src.domain.enums.publication import PublicationStatus


class FakePublicationRepo:
    def __init__(self, pubs: list[Publication]) -> None:
        self._store = {p.id: p for p in pubs}
        self.saved: list[Publication] = []

    async def get_by_id(self, publication_id: int):
        return self._store.get(publication_id)

    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]:
        return [p for p in self._store.values() if p.ad_id == ad_id]

    async def save(self, publication: Publication) -> None:
        self.saved.append(publication)
        self._store[publication.id] = publication


class FakeTaskQueue:
    def __init__(self) -> None:
        self.cancelled: list[str] = []

    async def cancel(self, *, job_id: str) -> bool:
        self.cancelled.append(job_id)
        return True


class FakeNotificationService:
    def __init__(self) -> None:
        self.notified: list[tuple[int, str]] = []

    async def notify_user(self, *, tg_id: int, text: str, reply_markup=None) -> None:
        self.notified.append((tg_id, text))


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


async def test_cancel_by_admin_cancels_entire_scheduled_series_and_notifies_owner():
    parent = Publication(
        id=1,
        ad_id=10,
        region_id=1,
        status=PublicationStatus.SCHEDULED,
        scheduler_job_id="job-1",
    )
    child_scheduled = Publication(
        id=2,
        ad_id=10,
        region_id=1,
        status=PublicationStatus.SCHEDULED,
        is_child=True,
        scheduler_job_id="job-2",
    )
    child_already_published = Publication(
        id=3, ad_id=10, region_id=1, status=PublicationStatus.PUBLISHED, is_child=True
    )

    repo = FakePublicationRepo([parent, child_scheduled, child_already_published])
    task_queue = FakeTaskQueue()
    notifications = FakeNotificationService()

    use_case = CancelPublicationByAdminUseCase(
        publication_repo=repo,
        task_queue=task_queue,
        notification_service=notifications,
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(
        CancelPublicationByAdminRequest(
            publication_id=1, owner_tg_id=555, label="О123ОВ77"
        )
    )

    assert parent.status == PublicationStatus.CANCELED
    assert child_scheduled.status == PublicationStatus.CANCELED
    # already-published child must be left alone
    assert child_already_published.status == PublicationStatus.PUBLISHED

    assert set(task_queue.cancelled) == {"job-1", "job-2"}
    assert len(notifications.notified) == 1
    tg_id, text = notifications.notified[0]
    assert tg_id == 555
    assert "О123ОВ77" in text
