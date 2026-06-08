from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base import Entity
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.exceptions.publication import (
    InvalidPublicationState,
    ServiceAlreadyAdded,
    ServiceNotAllowed,
)
from src.domain.value_objects.publication_plan import PublicationPlan
from src.domain.value_objects.slot_key import SlotKey


@dataclass(kw_only=True)
class Publication(Entity):
    """
    Публикация = то, что стоит в очереди/планировщике и будет отправлено в канал.
    Услуги покупаются именно к публикации.
    """

    ad_id: int
    region_id: int

    status: PublicationStatus = PublicationStatus.DRAFT

    # выбранный слот (локальная дата/время региона)
    slot: SlotKey | None = None

    # вычисленное время исполнения (в UTC) — будет нужно scheduler'у
    publish_at_utc: datetime | None = None

    # результат публикации
    channel_message_id: int | None = None
    published_at_utc: datetime | None = None

    scheduler_job_id: str | None = None

    plan: PublicationPlan | None = None
    services: list[PublicationService] = field(default_factory=list)

    def schedule(self, *, slot: SlotKey, publish_at_utc: datetime) -> None:
        if self.status not in (
            PublicationStatus.DRAFT,
            PublicationStatus.AWAITING_PAYMENT,
            PublicationStatus.SCHEDULED,
        ):
            raise InvalidPublicationState(f"Невозможно запланировать с {self.status}")
        self.slot = slot
        self.publish_at_utc = publish_at_utc
        self.status = PublicationStatus.SCHEDULED
        self.touch()

    def add_service(self, service: PublicationService) -> None:
        # запретим дубли по типу (если нужно — можно ослабить)
        if any(
            s.type == service.type and s.status == PublicationServiceStatus.ACTIVE
            for s in self.services
        ):
            raise ServiceAlreadyAdded(f"Услуга {service.type} уже добавлена")

        # PRIORITY можно добавлять только если публикация ещё не published/canceled
        if service.type == PublicationServiceType.PRIORITY_PUBLISH:
            if self.status in (
                PublicationStatus.PUBLISHED,
                PublicationStatus.CANCELED,
                PublicationStatus.REPLACED,
            ):
                raise ServiceNotAllowed(
                    "Услуга PRIORITY_PUBLISH нельзя добавить после публикации"
                )

        self.services.append(service)
        self.touch()

    def mark_publishing(self) -> None:
        if self.status != PublicationStatus.SCHEDULED:
            raise InvalidPublicationState(
                f"Невозможно начать публикацию из {self.status}"
            )
        self.status = PublicationStatus.PUBLISHING
        self.touch()

    def mark_published(self, *, message_id: int, published_at_utc: datetime) -> None:
        if self.status not in (
            PublicationStatus.PUBLISHING,
            PublicationStatus.SCHEDULED,
        ):
            # иногда воркер может пропустить промежуточный статус
            raise InvalidPublicationState(f"Невозможно опубликовать из {self.status}")
        self.channel_message_id = message_id
        self.published_at_utc = published_at_utc
        self.status = PublicationStatus.PUBLISHED
        self.touch()

    def mark_failed(self) -> None:
        if self.status not in (
            PublicationStatus.PUBLISHING,
            PublicationStatus.SCHEDULED,
        ):
            raise InvalidPublicationState(f"Невозможно опубликовать из {self.status}")
        self.status = PublicationStatus.FAILED
        self.touch()

    def cancel(self) -> None:
        if self.status in (PublicationStatus.PUBLISHED, PublicationStatus.REPLACED):
            raise InvalidPublicationState(
                f"Невозможно отменить публикацию из {self.status}"
            )
        self.status = PublicationStatus.CANCELED
        self.touch()

    def mark_replaced_by_priority(self) -> None:
        # когда сделали publish now и старую "очередную" нужно убрать
        if self.status in (PublicationStatus.PUBLISHED, PublicationStatus.CANCELED):
            raise InvalidPublicationState(f"Невозможно заменить {self.status}")
        self.status = PublicationStatus.REPLACED
        self.touch()

    def set_slot_pending_payment(
        self,
        *,
        slot: SlotKey,
        publish_at_utc: datetime,
    ) -> None:
        if self.status not in (
            PublicationStatus.DRAFT,
            PublicationStatus.AWAITING_PAYMENT,
        ):
            raise InvalidPublicationState(
                f"Не удается установить интервал ожидания платежа с {self.status}"
            )
        self.slot = slot
        self.publish_at_utc = publish_at_utc
        self.status = PublicationStatus.AWAITING_PAYMENT
        self.touch()

    def set_scheduler_job(self, job_id: str) -> None:
        self.scheduler_job_id = job_id
        self.touch()

    def clear_scheduler_job(self) -> None:
        self.scheduler_job_id = None
        self.touch()

    def has_active_service(self, service_type: PublicationServiceType) -> bool:
        return any(
            s.type == service_type and s.status == PublicationServiceStatus.ACTIVE
            for s in self.services
        )