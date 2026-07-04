from dataclasses import dataclass

from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.publication_service.image_processor import ImageProcessor
from src.application.ports.telegram.telegram_publisher import TelegramPublisher
from src.domain.entities.ad import Ad
from src.domain.entities.region import Region
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver


@dataclass
class ServiceContext:
    region: Region
    ad: Ad
    scheduler: Scheduler
    telegram: TelegramPublisher
    publication_repo: PublicationRepository
    time_resolver: PublishTimeResolver
    image_processor: ImageProcessor
    tg_id: int
    caption: str
    highlight_file_id: str | None = None
