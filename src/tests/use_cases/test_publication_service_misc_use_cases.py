"""
Coverage for the remaining publication_service use cases: AddRedFrameUseCase,
AddServiceToPublicationUseCase, GetAdIdsWithActiveAutopublishSeriesUseCase,
UnpinMessageUseCase — previously untested.
"""

import pytest

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.use_cases.publication_service.add_red_frame import (
    AddRedFrameUseCase,
)
from src.application.use_cases.publication_service.add_service_to_publication import (
    AddServiceToPublicationRequest,
    AddServiceToPublicationUseCase,
)
from src.application.use_cases.publication_service.get_ad_ids_with_active_autipublish_series import (
    GetAdIdsWithActiveAutopublishSeriesRequest,
    GetAdIdsWithActiveAutopublishSeriesUseCase,
)
from src.application.use_cases.publication_service.unpin_message import (
    UnpinMessageRequest,
    UnpinMessageUseCase,
)
from src.domain.entities.publication import Publication
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType


class FakeImageProcessor:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    async def add_red_frame(self, *, chat_id: int, file_id: str) -> str:
        self.calls.append((chat_id, file_id))
        return f"framed-{file_id}"


class FakePublicationRepo:
    def __init__(self, pubs: list[Publication] | None = None) -> None:
        self._store = {p.id: p for p in (pubs or [])}
        self.saved: list[Publication] = []
        self.autopublish_series_result: set[int] = set()

    async def get_by_id(self, publication_id: int) -> Publication | None:
        return self._store.get(publication_id)

    async def save(self, publication: Publication) -> None:
        self.saved.append(publication)

    async def get_ad_ids_with_active_autopublish_series(
        self, ad_ids: list[int]
    ) -> set[int]:
        return self.autopublish_series_result


class FakeServiceDefRepo:
    def __init__(self, definition: ServiceDefinition) -> None:
        self._definition = definition

    async def get_by_type(self, service_type) -> ServiceDefinition:
        return self._definition


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


class FakeTelegramPublisher:
    def __init__(self) -> None:
        self.unpinned: list[tuple[int, int]] = []

    async def unpin_message(self, *, channel_id: int, message_id: int) -> None:
        self.unpinned.append((channel_id, message_id))


def make_service_definition(**overrides) -> ServiceDefinition:
    defaults = dict(
        id=1, title="PIN", type=PublicationServiceType.PIN, price=100, is_active=True
    )
    defaults.update(overrides)
    return ServiceDefinition(**defaults)


# ---------- AddRedFrameUseCase ----------


async def test_add_red_frame_delegates_to_image_processor():
    processor = FakeImageProcessor()
    use_case = AddRedFrameUseCase(image_processor=processor)

    result = await use_case.execute(chat_id=555, image_file_id="orig-file")

    assert result.image_file_id == "framed-orig-file"
    assert processor.calls == [(555, "orig-file")]


# ---------- AddServiceToPublicationUseCase ----------


async def test_add_service_to_publication_attaches_service():
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    definition = make_service_definition(type=PublicationServiceType.PIN)
    use_case = AddServiceToPublicationUseCase(
        publication_repo=FakePublicationRepo([pub]),
        service_def_repo=FakeServiceDefRepo(definition),
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(
        AddServiceToPublicationRequest(
            publication_id=1, service_type=PublicationServiceType.PIN
        )
    )

    assert len(pub.services) == 1
    assert pub.services[0].type == PublicationServiceType.PIN


async def test_add_service_to_publication_rejects_inactive_service():
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    definition = make_service_definition(is_active=False)
    use_case = AddServiceToPublicationUseCase(
        publication_repo=FakePublicationRepo([pub]),
        service_def_repo=FakeServiceDefRepo(definition),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ValueError):
        await use_case(
            AddServiceToPublicationRequest(
                publication_id=1, service_type=PublicationServiceType.PIN
            )
        )


async def test_add_service_to_publication_unknown_publication_raises():
    definition = make_service_definition()
    use_case = AddServiceToPublicationUseCase(
        publication_repo=FakePublicationRepo([]),
        service_def_repo=FakeServiceDefRepo(definition),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(PublicationNotFoundException):
        await use_case(
            AddServiceToPublicationRequest(
                publication_id=1, service_type=PublicationServiceType.PIN
            )
        )


# ---------- GetAdIdsWithActiveAutopublishSeriesUseCase ----------


async def test_get_ad_ids_with_active_autopublish_series_delegates_to_repo():
    repo = FakePublicationRepo()
    repo.autopublish_series_result = {1, 3}
    use_case = GetAdIdsWithActiveAutopublishSeriesUseCase(publication_repo=repo)

    result = await use_case(
        GetAdIdsWithActiveAutopublishSeriesRequest(ad_ids=[1, 2, 3])
    )

    assert result == {1, 3}


# ---------- UnpinMessageUseCase ----------


async def test_unpin_message_delegates_to_telegram():
    telegram = FakeTelegramPublisher()
    use_case = UnpinMessageUseCase(telegram=telegram)

    await use_case(UnpinMessageRequest(channel_id=-100123, message_id=999))

    assert telegram.unpinned == [(-100123, 999)]
