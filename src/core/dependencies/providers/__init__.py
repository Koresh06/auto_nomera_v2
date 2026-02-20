from src.core.dependencies.providers.mediator import MediatorProvider
from src.core.dependencies.providers.repositories import RepositoriesProvider
from src.core.dependencies.providers.services import ServicesProvider
from src.core.dependencies.providers.taskiq import TaskiqProvider
from src.core.dependencies.providers.base import BaseAppProvider
from src.core.dependencies.providers.telegram import TelegramProvider
from src.core.dependencies.providers.telegram_publicher import TelegramPublisherProvider
from src.core.dependencies.providers.use_cases import UseCasesProvider


def make_base_providers():
    return (
        BaseAppProvider(),
        RepositoriesProvider(),
        ServicesProvider(),
        UseCasesProvider(),
        TaskiqProvider(),
        MediatorProvider(),
        TelegramProvider(),
        TelegramPublisherProvider(),
    )