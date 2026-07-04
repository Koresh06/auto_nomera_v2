from src.domain.enums.publication_service import PublicationServiceType
from src.application.services.publication.strategies.autopublish import (
    AutopublishStrategy,
)
from src.application.services.publication.strategies.highlight import HighlightStrategy
from src.application.services.publication.strategies.pin import PinStrategy
from src.application.services.publication.strategy import PublicationServiceStrategy


STRATEGIES: dict[PublicationServiceType, PublicationServiceStrategy] = {
    PublicationServiceType.HIGHLIGHT: HighlightStrategy(),
    PublicationServiceType.PIN: PinStrategy(),
    PublicationServiceType.AUTOPUBLISH: AutopublishStrategy(),
}
