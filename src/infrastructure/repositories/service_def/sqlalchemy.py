from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.exceptions.service_definition import ServiceDefinitionException
from src.application.ports.publication_service.service_definition_repo import ServiceDefinitionRepository
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType
from src.infrastructure.database.models.service_definition import ServiceDefinitionModel


class SQLAlchemyServiceDefinitionRepo(ServiceDefinitionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_type(self, service_type: PublicationServiceType) -> ServiceDefinition:
        result = await self._session.execute(
            select(ServiceDefinitionModel).where(
                ServiceDefinitionModel.type == service_type
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ServiceDefinitionException(f"ServiceDefinition type={service_type} not found")
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
                ServiceDefinitionModel.is_active == True
            )
        )
        return [m.to_entity() for m in result.scalars().all()]

    async def create(self, service: ServiceDefinition) -> ServiceDefinition:
        model = ServiceDefinitionModel.from_entity(service)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()

    async def update(
        self,
        service_type: PublicationServiceType,
        *,
        title: str | None = None,
        price: int | None = None,
        is_active: bool | None = None,
        description: str | None = None,
    ) -> ServiceDefinition:
        result = await self._session.execute(
            select(ServiceDefinitionModel).where(
                ServiceDefinitionModel.type == service_type
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ServiceDefinitionException(f"ServiceDefinition type={service_type} not found")

        if title is not None:
            model.title = title
        if price is not None:
            model.price = price
        if is_active is not None:
            model.is_active = is_active
        if description is not None:
            model.description = description

        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()
    

    async def get_by_id(self, service_id: int) -> ServiceDefinition:
        result = await self._session.execute(
            select(ServiceDefinitionModel).where(
                ServiceDefinitionModel.id == service_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ServiceDefinitionException(f"ServiceDefinition id={service_id} not found")
        return model.to_entity()