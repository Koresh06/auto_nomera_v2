from src.core.dependencies.providers.base import BaseAppProvider
from src.core.dependencies.providers.mediator import MediatorProvider, FakeMediatorProvider
from src.core.dependencies.providers.use_cases import UseCasesProvider
from src.core.dependencies.providers.telegram import TgBotProvider


def make_base_providers():
    return (
        BaseAppProvider(),
        # UseCasesProvider(),
        # MediatorProvider(),
        FakeMediatorProvider(),
        TgBotProvider(),
    )