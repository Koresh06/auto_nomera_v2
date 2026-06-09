import logging

from src.application.mediator import Mediator
from src.application.use_cases.seeds.service_definitions import SeedServiceDefinitionsRequest


logger = logging.getLogger(__name__)


async def run_seeds(mediator: Mediator) -> None:
    logger.info("[Seeds] Running seeds...")
    await mediator.handle(SeedServiceDefinitionsRequest())
    logger.info("[Seeds] Done.")