from src.application.ports.region.region_repo import RegionRepository
from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName


region_1 = Region(
    id=1,
    title="Минск",
    timezone=TimezoneName("Europe/Minsk"),
    channel_id=-100123456789,
    channel_username="avtonomera126_26",
    status=RegionStatus.ACTIVE,
    settings=RegionSettings(),
    metadata=RegionMetadata(
        data={
            "tg_group_url": "https://t.me/avtonomera126_26",
            "vk_group_url": "https://vk.com/26gosnomera126",
            "max_channel_url": "https://t.me/avtonomera126_26",
        }
    ),
)


class InMemoryRegionRepo(RegionRepository):
    def __init__(self, regions: list[Region] | None) -> None:
        if regions is None:
            self._items = {}
        else:
            self._items = {r.id: r for r in regions}

    async def get_by_id(self, region_id: int) -> Region:
        return self._items[region_id]

    async def get_all(self) -> list[Region]:
        return list(self._items.values())
