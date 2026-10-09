"""
Coverage for src/application/use_cases/region/* and the region sorting rule
(src/domain/services/region/sorting.py) — previously entirely untested.
"""

from decimal import Decimal

import pytest

from src.application.dtos.region import RegionDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.use_cases.region.create import (
    CreateRegionCommand,
    CreateRegionUseCase,
)
from src.application.use_cases.region.get_all import (
    GetAllRegionsUseCase,
    GetRegionsRequest,
)
from src.application.use_cases.region.get_by_id import (
    GegByIdRegionUseCase,
    IdRegionRequest,
)
from src.application.use_cases.region.toggle_status import (
    ToggleRegionStatusCommand,
    ToggleRegionStatusUseCase,
)
from src.application.use_cases.region.update_metadata import (
    UpdateRegionMetadataCommand,
    UpdateRegionMetadataUseCase,
)
from src.application.use_cases.region.update_settings import (
    UpdateRegionSettingsCommand,
    UpdateRegionSettingsUseCase,
)
from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus
from src.domain.services.region.sorting import sort_regions
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName


class FakeRegionRepo:
    def __init__(self, regions: list[Region] | None = None) -> None:
        self._store = {r.id: r for r in (regions or [])}
        self._next_id = 100
        self.created: list[Region] = []
        self.updated: list[Region] = []

    async def get_by_id(self, region_id: int) -> Region | None:
        return self._store.get(region_id)

    async def get_all(self) -> list[Region]:
        return list(self._store.values())

    async def create(self, region: Region) -> Region:
        region.id = self._next_id
        self._next_id += 1
        self._store[region.id] = region
        self.created.append(region)
        return region

    async def update(self, region: Region) -> Region:
        self._store[region.id] = region
        self.updated.append(region)
        return region


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


def make_region(**overrides) -> Region:
    defaults = dict(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        status=RegionStatus.ACTIVE,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )
    defaults.update(overrides)
    return Region(**defaults)


# ---------- CreateRegionUseCase ----------


async def test_create_region_persists_and_returns_dto():
    repo = FakeRegionRepo()
    use_case = CreateRegionUseCase(
        region_repo=repo, transaction_manager=FakeTransactionManager()
    )

    dto = await use_case(
        CreateRegionCommand(
            title="  Новый регион  ",
            timezone="Europe/Moscow",
            channel_id=-1009999,
            channel_username="newregion",
            metadata=RegionMetadata(),
        )
    )

    assert dto.title == "Новый регион"  # Region.create() strips whitespace
    assert len(repo.created) == 1


async def test_create_region_rejects_zero_channel_id():
    repo = FakeRegionRepo()
    use_case = CreateRegionUseCase(
        region_repo=repo, transaction_manager=FakeTransactionManager()
    )

    with pytest.raises(Exception):
        await use_case(
            CreateRegionCommand(
                title="Title",
                timezone="Europe/Moscow",
                channel_id=0,
                channel_username="x",
                metadata=RegionMetadata(),
            )
        )


# ---------- GetAllRegionsUseCase / sort_regions ----------


async def test_get_all_regions_sorts_moscow_first():
    msk = make_region(id=1, title="|77|Москва", channel_username="msk77")
    spb = make_region(id=2, title="|78|Питер", channel_username="spb78")
    other = make_region(id=3, title="|23|Краснодар", channel_username="krd23")
    use_case = GetAllRegionsUseCase(region_repo=FakeRegionRepo([other, spb, msk]))

    result = await use_case(GetRegionsRequest())

    titles = [r.title for r in result]
    assert (
        titles.index("|77|Москва")
        < titles.index("|78|Питер")
        < titles.index("|23|Краснодар")
    )


def test_sort_regions_moscow_before_spb_before_others():
    msk = RegionDTO(
        id=1,
        title="|77|Москва",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-1,
        channel_username="msk",
        status=RegionStatus.ACTIVE,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )
    spb = RegionDTO(
        id=2,
        title="|78|Питер",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-2,
        channel_username="spb",
        status=RegionStatus.ACTIVE,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )
    other = RegionDTO(
        id=3,
        title="|23|Краснодар",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-3,
        channel_username="krd",
        status=RegionStatus.ACTIVE,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )

    result = sort_regions([other, spb, msk])

    assert result == [msk, spb, other]


# ---------- GegByIdRegionUseCase ----------


async def test_get_by_id_region_raises_when_missing():
    use_case = GegByIdRegionUseCase(region_repo=FakeRegionRepo())
    with pytest.raises(RegionNotFoundException):
        await use_case(IdRegionRequest(region_id=1))


async def test_get_by_id_region_returns_dto():
    use_case = GegByIdRegionUseCase(region_repo=FakeRegionRepo([make_region()]))
    dto = await use_case(IdRegionRequest(region_id=1))
    assert dto.id == 1


# ---------- ToggleRegionStatusUseCase ----------


async def test_toggle_region_status_disables_active_region():
    region = make_region(status=RegionStatus.ACTIVE)
    use_case = ToggleRegionStatusUseCase(
        region_repo=FakeRegionRepo([region]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(ToggleRegionStatusCommand(region_id=1))

    assert dto.status == RegionStatus.DISABLED


async def test_toggle_region_status_enables_disabled_region():
    region = make_region(status=RegionStatus.DISABLED)
    use_case = ToggleRegionStatusUseCase(
        region_repo=FakeRegionRepo([region]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(ToggleRegionStatusCommand(region_id=1))

    assert dto.status == RegionStatus.ACTIVE


async def test_toggle_region_status_unknown_region_raises():
    use_case = ToggleRegionStatusUseCase(
        region_repo=FakeRegionRepo(), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(RegionNotFoundException):
        await use_case(ToggleRegionStatusCommand(region_id=1))


# ---------- UpdateRegionMetadataUseCase ----------


async def test_update_region_metadata_only_changes_provided_fields():
    region = make_region(
        metadata=RegionMetadata(
            tg_group_url="https://t.me/old", vk_group_url="https://vk.com/old"
        )
    )
    use_case = UpdateRegionMetadataUseCase(
        region_repo=FakeRegionRepo([region]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(
        UpdateRegionMetadataCommand(region_id=1, tg_group_url="https://t.me/new")
    )

    assert dto.metadata.tg_group_url == "https://t.me/new"
    # vk_group_url wasn't passed (UNSET) — must be left untouched
    assert dto.metadata.vk_group_url == "https://vk.com/old"


async def test_update_region_metadata_unknown_region_raises():
    use_case = UpdateRegionMetadataUseCase(
        region_repo=FakeRegionRepo(), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(RegionNotFoundException):
        await use_case(UpdateRegionMetadataCommand(region_id=1))


# ---------- UpdateRegionSettingsUseCase ----------


async def test_update_region_settings_only_changes_provided_fields():
    region = make_region(
        settings=RegionSettings(system_paid_slots_count=3, days_range=7)
    )
    use_case = UpdateRegionSettingsUseCase(
        region_repo=FakeRegionRepo([region]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(
        UpdateRegionSettingsCommand(region_id=1, system_paid_slots_count=1)
    )

    assert dto.settings.system_paid_slots_count == 1
    assert dto.settings.days_range == 7  # unchanged (UNSET)


async def test_update_region_settings_paid_slot_price():
    region = make_region()
    use_case = UpdateRegionSettingsUseCase(
        region_repo=FakeRegionRepo([region]),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(
        UpdateRegionSettingsCommand(region_id=1, paid_slot_price=Decimal("299"))
    )

    assert dto.settings.paid_slot_price == Decimal("299")


async def test_update_region_settings_unknown_region_raises():
    use_case = UpdateRegionSettingsUseCase(
        region_repo=FakeRegionRepo(), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(RegionNotFoundException):
        await use_case(UpdateRegionSettingsCommand(region_id=1))
