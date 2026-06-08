from src.domain.enums.publication_service import PublicationServiceType
from src.domain.services.publication_service.strategies.autopublish import AutopublishStrategy
from src.domain.services.publication_service.strategies.highlight import HighlightStrategy
from src.domain.services.publication_service.strategies.pin import PinStrategy
from src.domain.services.publication_service.strategy import PublicationServiceStrategy


STRATEGIES: dict[PublicationServiceType, PublicationServiceStrategy] = {
    PublicationServiceType.HIGHLIGHT: HighlightStrategy(),
    PublicationServiceType.PIN: PinStrategy(),
    PublicationServiceType.AUTOPUBLISH: AutopublishStrategy(),
}