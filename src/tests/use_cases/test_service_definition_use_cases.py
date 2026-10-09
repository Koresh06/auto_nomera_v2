"""
Coverage for src/application/use_cases/service_difinition/* — previously
entirely untested.
"""

import pytest

from src.application.exceptions.service_definition import (
    ServiceDefinitionNotFoundException,
)
from src.application.use_cases.service_difinition.get_all import (
    GetAllServicesRequest,
    GetAllServicesUseCase,
)
from src.application.use_cases.service_difinition.get_by_id import (
    GetByIdServiceDefinitionRequest,
    GetByIdServiceDefinitionUseCase,
)
from src.application.use_cases.service_difinition.toggle_status import (
    ToggleServiceStatusCommand,
    ToggleServiceStatusUseCase,
)
from src.application.use_cases.service_difinition.update import (
    UpdateServiceCommand,
    UpdateServiceUseCase,
)
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType


class FakeServiceDefRepo:
    def __init__(self, services: list[ServiceDefinition] | None = None) -> None:
        self._store = {s.id: s for s in (services or [])}

    async def get_all(self, is_active: bool | None = None) -> list[ServiceDefinition]:
        values = list(self._store.values())
        if is_active is None:
            return values
        return [s for s in values if s.is_active == is_active]

    async def get_by_id(self, service_id: int) -> ServiceDefinition | None:
        return self._store.get(service_id)

    async def save(self, service: ServiceDefinition) -> ServiceDefinition:
        self._store[service.id] = service
        return service


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


def make_service(**overrides) -> ServiceDefinition:
    defaults = dict(
        id=1,
        title="PIN",
        type=PublicationServiceType.PIN,
        price=100,
        is_active=True,
    )
    defaults.update(overrides)
    return ServiceDefinition(**defaults)


# ---------- GetAllServicesUseCase ----------


async def test_get_all_services_no_filter_returns_everything():
    active = make_service(id=1, is_active=True)
    inactive = make_service(id=2, is_active=False)
    use_case = GetAllServicesUseCase(
        service_def_repo=FakeServiceDefRepo([active, inactive])
    )

    result = await use_case(GetAllServicesRequest())

    assert len(result) == 2


async def test_get_all_services_filters_by_active():
    active = make_service(id=1, is_active=True)
    inactive = make_service(id=2, is_active=False)
    use_case = GetAllServicesUseCase(
        service_def_repo=FakeServiceDefRepo([active, inactive])
    )

    result = await use_case(GetAllServicesRequest(is_active=True))

    assert len(result) == 1
    assert result[0].id == 1


# ---------- GetByIdServiceDefinitionUseCase ----------


async def test_get_by_id_service_definition_raises_when_missing():
    use_case = GetByIdServiceDefinitionUseCase(service_def_repo=FakeServiceDefRepo())
    with pytest.raises(ValueError):
        await use_case(GetByIdServiceDefinitionRequest(id=1))


async def test_get_by_id_service_definition_returns_dto():
    use_case = GetByIdServiceDefinitionUseCase(
        service_def_repo=FakeServiceDefRepo([make_service()])
    )
    dto = await use_case(GetByIdServiceDefinitionRequest(id=1))
    assert dto.id == 1


# ---------- ToggleServiceStatusUseCase ----------


async def test_toggle_service_status_deactivates_active_service():
    service = make_service(is_active=True)
    use_case = ToggleServiceStatusUseCase(
        service_repo=FakeServiceDefRepo([service]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(ToggleServiceStatusCommand(service_id=1))

    assert dto.is_active is False


async def test_toggle_service_status_activates_inactive_service():
    service = make_service(is_active=False)
    use_case = ToggleServiceStatusUseCase(
        service_repo=FakeServiceDefRepo([service]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(ToggleServiceStatusCommand(service_id=1))

    assert dto.is_active is True


async def test_toggle_service_status_unknown_service_raises():
    use_case = ToggleServiceStatusUseCase(
        service_repo=FakeServiceDefRepo(), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(ServiceDefinitionNotFoundException):
        await use_case(ToggleServiceStatusCommand(service_id=1))


# ---------- UpdateServiceUseCase ----------


async def test_update_service_only_changes_provided_fields():
    service = make_service(title="Old title", price=100, duration_days=7)
    use_case = UpdateServiceUseCase(
        service_repo=FakeServiceDefRepo([service]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(UpdateServiceCommand(service_id=1, title="New title"))

    assert dto.title == "New title"
    assert dto.price == 100  # unchanged (UNSET)
    assert dto.duration_days == 7  # unchanged (UNSET)


async def test_update_service_price_validation_rejects_negative():
    service = make_service(price=100)
    use_case = UpdateServiceUseCase(
        service_repo=FakeServiceDefRepo([service]),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ValueError):
        await use_case(UpdateServiceCommand(service_id=1, price=-5))


async def test_update_service_can_clear_duration_to_none():
    service = make_service(duration_days=7)
    use_case = UpdateServiceUseCase(
        service_repo=FakeServiceDefRepo([service]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(UpdateServiceCommand(service_id=1, duration_days=None))

    assert dto.duration_days is None


async def test_update_service_unknown_service_raises():
    use_case = UpdateServiceUseCase(
        service_repo=FakeServiceDefRepo(), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(ServiceDefinitionNotFoundException):
        await use_case(UpdateServiceCommand(service_id=1, title="X"))
