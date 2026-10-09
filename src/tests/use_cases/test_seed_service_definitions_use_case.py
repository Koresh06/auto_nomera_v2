"""
Coverage for src/application/use_cases/seeds/service_definitions.py —
previously entirely untested.
"""

from src.application.use_cases.seeds.service_definitions import (
    SeedServiceDefinitionsRequest,
    SeedServiceDefinitionsUseCase,
)
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType
from src.infrastructure.seeds.service_definitions import DEFAULT_SERVICES


class FakeServiceDefRepo:
    def __init__(self, existing: list[ServiceDefinition] | None = None) -> None:
        self._store = list(existing or [])
        self.created: list[ServiceDefinition] = []

    async def get_all(self) -> list[ServiceDefinition]:
        return self._store

    async def create(self, definition: ServiceDefinition) -> ServiceDefinition:
        self.created.append(definition)
        self._store.append(definition)
        return definition


class FakeTransactionManager:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


def make_service_definition(**overrides) -> ServiceDefinition:
    defaults = dict(
        id=1,
        type=PublicationServiceType.PIN,
        title="PIN",
        price=100,
        is_active=True,
    )
    defaults.update(overrides)
    return ServiceDefinition(**defaults)


async def test_seed_service_definitions_creates_all_when_none_exist():
    repo = FakeServiceDefRepo([])
    tx = FakeTransactionManager()
    use_case = SeedServiceDefinitionsUseCase(
        service_def_repo=repo, transaction_manager=tx
    )

    await use_case(SeedServiceDefinitionsRequest())

    assert len(repo.created) == len(DEFAULT_SERVICES)
    created_types = {d.type for d in repo.created}
    assert created_types == {data["type"] for data in DEFAULT_SERVICES}
    assert tx.committed is True


async def test_seed_service_definitions_skips_existing_types():
    existing = make_service_definition(type=PublicationServiceType.PIN)
    repo = FakeServiceDefRepo([existing])
    tx = FakeTransactionManager()
    use_case = SeedServiceDefinitionsUseCase(
        service_def_repo=repo, transaction_manager=tx
    )

    await use_case(SeedServiceDefinitionsRequest())

    created_types = {d.type for d in repo.created}
    assert PublicationServiceType.PIN not in created_types
    assert len(repo.created) == len(DEFAULT_SERVICES) - 1


async def test_seed_service_definitions_is_noop_when_all_exist():
    existing = [
        make_service_definition(id=i, type=data["type"])
        for i, data in enumerate(DEFAULT_SERVICES, start=1)
    ]
    repo = FakeServiceDefRepo(existing)
    tx = FakeTransactionManager()
    use_case = SeedServiceDefinitionsUseCase(
        service_def_repo=repo, transaction_manager=tx
    )

    await use_case(SeedServiceDefinitionsRequest())

    assert repo.created == []
    assert tx.committed is True
