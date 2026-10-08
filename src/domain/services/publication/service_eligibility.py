from src.domain.enums.ad import AdType
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.exceptions.publication import ServiceNotAllowed


def ensure_service_allowed_for_ad_type(
    *, service_type: PublicationServiceType, ad_type: AdType
) -> None:
    """HIGHLIGHT выделяет картинку объявления — у STORE нет единого
    изображения объявления (список товаров с отдельными ценами), поэтому
    услуга для него не имеет смысла. Раньше это проверялось только в одном
    use case (publish_publication.py) и в UI-фильтрации списка услуг — любой
    другой путь оплаты/применения услуги мог списать деньги без эффекта.
    """
    if service_type == PublicationServiceType.HIGHLIGHT and ad_type == AdType.STORE:
        raise ServiceNotAllowed(
            f"{service_type.value} недоступна для объявлений типа {ad_type.value}"
        )
