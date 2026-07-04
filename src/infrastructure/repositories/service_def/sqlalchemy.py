from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.exceptions.service_definition import ServiceDefinitionException
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType
from src.infrastructure.database.models.service_definition import ServiceDefinitionModel


class SQLAlchemyServiceDefinitionRepo(ServiceDefinitionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_type(
        self, service_type: PublicationServiceType
    ) -> ServiceDefinition:
        result = await self._session.execute(
            select(ServiceDefinitionModel).where(
                ServiceDefinitionModel.type == service_type
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ServiceDefinitionException(
                f"ServiceDefinition type={service_type} not found"
            )
        return model.to_entity()

    async def get_all(self, is_active: bool | None = None) -> list[ServiceDefinition]:
        if is_active is not None:
            result = await self._session.execute(
                select(ServiceDefinitionModel).where(
                    ServiceDefinitionModel.is_active == is_active
                )
            )
            return [m.to_entity() for m in result.scalars().all()]

        result = await self._session.execute(select(ServiceDefinitionModel))
        return [m.to_entity() for m in result.scalars().all()]

    async def get_all_active(self) -> list[ServiceDefinition]:
        result = await self._session.execute(
            select(ServiceDefinitionModel).where(
                ServiceDefinitionModel.is_active.is_(True)
            )
        )
        return [m.to_entity() for m in result.scalars().all()]

    async def get_by_id(self, service_id: int) -> ServiceDefinition:
        result = await self._session.execute(
            select(ServiceDefinitionModel).where(
                ServiceDefinitionModel.id == service_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ServiceDefinitionException(
                f"ServiceDefinition id={service_id} not found"
            )
        return model.to_entity()

    async def create(self, service: ServiceDefinition) -> ServiceDefinition:
        model = ServiceDefinitionModel.from_entity(service)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()

    async def save(self, service: ServiceDefinition) -> ServiceDefinition:
        query = select(ServiceDefinitionModel).where(
            ServiceDefinitionModel.id == service.id
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            raise ServiceDefinitionException(
                f"ServiceDefinition id={service.id} not found"
            )
        ServiceDefinitionModel._update_model(model, service)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()
