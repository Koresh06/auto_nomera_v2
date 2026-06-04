from dataclasses import dataclass

from src.domain.entities.base import Entity
from src.domain.enums.publication_service import PublicationServiceType


@dataclass(kw_only=True)
class ServiceDefinition(Entity):
    """
    Каталог услуг (продукт).
    Это НЕ то, что купил пользователь. Это то, что админ настраивает:
    цена, активность, дефолтные настройки и т.д.
    """

    type: PublicationServiceType
    title: str
    price: int
    is_active: bool = True
    description: str | None = None
    params_schema: dict | None = None
