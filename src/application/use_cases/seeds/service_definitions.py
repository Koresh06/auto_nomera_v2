import logging
from dataclasses import dataclass

from src.domain.entities.service_definition import ServiceDefinition
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager
from src.infrastructure.seeds.service_definitions import DEFAULT_SERVICES


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class SeedServiceDefinitionsRequest(UseCaseRequest):
    pass


@dataclass(kw_only=True)
class SeedServiceDefinitionsUseCase(UseCase[SeedServiceDefinitionsRequest, None]):
    service_def_repo: ServiceDefinitionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: SeedServiceDefinitionsRequest) -> None:
        existing = await self.service_def_repo.get_all()
        existing_types = {s.type for s in existing}

        for data in DEFAULT_SERVICES:
            if data["type"] in existing_types:
                continue  # не перезаписываем существующие

            await self.service_def_repo.create(
                ServiceDefinition(
                    type=data["type"],
                    title=data["title"],
                    price=data["price"],
                    duration_days=data["duration_days"],
                    description=data["description"],
                )
            )

        await self.transaction_manager.commit()
        logger.info(
            f"[SeedServiceDefinitions:done] seeded {len(DEFAULT_SERVICES)} services"
        )
