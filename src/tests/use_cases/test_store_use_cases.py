"""
Coverage for src/application/use_cases/store/* — previously entirely untested.
"""

import pytest

from src.application.exceptions.ad import AdNotFoundException
from src.application.exceptions.store import (
    StoreAlreadyExistsException,
    StoreItemsAlreadyExistException,
)
from src.application.use_cases.store.add_items import (
    AddStoreItemsRequest,
    AddStoreItemsUseCase,
)
from src.application.use_cases.store.create import (
    CreateStoreRequest,
    CreateStoreUseCase,
)
from src.application.use_cases.store.delete_items import (
    DeleteStoreItemRequest,
    DeleteStoreItemUseCase,
)
from src.application.use_cases.store.get_by_user import (
    GetUserStoreRequest,
    GetUserStoreUseCase,
)
from src.application.use_cases.store.update_items import (
    UpdateStoreItemRequest,
    UpdateStoreItemUseCase,
)
from src.application.use_cases.store.update_store import (
    UpdateStoreRequest,
    UpdateStoreUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.region import Region
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.region import RegionStatus
from src.domain.exceptions.region import RegionDisabledError
from src.domain.services.region.region_guard import RegionGuard
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.store_content import StoreContent, StoreItem
from src.domain.value_objects.timezone_name import TimezoneName


class FakeAdRepo:
    def __init__(self, ads: list[Ad] | None = None) -> None:
        self._store = {a.id: a for a in (ads or [])}
        self._next_id = 100
        self.created: list[Ad] = []
        self.saved: list[Ad] = []

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._store.get(ad_id)

    async def create(self, ad: Ad) -> Ad:
        ad.id = self._next_id
        self._next_id += 1
        self._store[ad.id] = ad
        self.created.append(ad)
        return ad

    async def save(self, ad: Ad) -> None:
        self.saved.append(ad)
        self._store[ad.id] = ad

    async def find_store_by_user(self, user_id: int, region_id: int) -> Ad | None:
        for ad in self._store.values():
            if (
                ad.user_id == user_id
                and ad.region_id == region_id
                and ad.ad_type == AdType.STORE
            ):
                return ad
        return None


class FakeRegionRepo:
    def __init__(self, region: Region | None) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


def make_region(status: RegionStatus = RegionStatus.ACTIVE) -> Region:
    return Region(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        status=status,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )


def make_store_ad(items: tuple[StoreItem, ...] = (), **overrides) -> Ad:
    defaults = dict(
        id=1, user_id=1, region_id=1, ad_type=AdType.STORE, status=AdStatus.READY
    )
    defaults.update(overrides)
    ad = Ad(**defaults)
    ad.fill_store_content(
        StoreContent(
            shop_name="Shop",
            city="City",
            contacts=Contacts(username="shop"),
            items=items,
        )
    )
    return ad


# ---------- CreateStoreUseCase ----------


async def test_create_store_succeeds_for_new_user():
    region = make_region()
    repo = FakeAdRepo()
    use_case = CreateStoreUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        ad_repo=repo,
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(
        CreateStoreRequest(
            user_id=1,
            region_id=1,
            shop_name="My Shop",
            city="City",
            contacts=Contacts(username="shop"),
        )
    )

    assert dto.store_content.shop_name == "My Shop"
    assert len(repo.created) == 1


async def test_create_store_raises_if_already_exists():
    region = make_region()
    existing = make_store_ad()
    use_case = CreateStoreUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        ad_repo=FakeAdRepo([existing]),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(StoreAlreadyExistsException):
        await use_case(
            CreateStoreRequest(
                user_id=1,
                region_id=1,
                shop_name="Another",
                city="City",
                contacts=Contacts(),
            )
        )


async def test_create_store_raises_if_region_disabled():
    region = make_region(status=RegionStatus.DISABLED)
    use_case = CreateStoreUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        ad_repo=FakeAdRepo(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(RegionDisabledError):
        await use_case(
            CreateStoreRequest(
                user_id=1, region_id=1, shop_name="X", city="Y", contacts=Contacts()
            )
        )


# ---------- AddStoreItemsUseCase ----------


async def test_add_store_items_appends_new_items():
    ad = make_store_ad(items=(StoreItem(plate="А001АА77", price=Price(100_000)),))
    use_case = AddStoreItemsUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    result = await use_case(
        AddStoreItemsRequest(
            ad_id=1, items=[StoreItem(plate="В002ВВ77", price=Price(200_000))]
        )
    )

    assert result.added_count == 1
    assert len(result.ad.store_content.items) == 2


async def test_add_store_items_rejects_duplicate_plates():
    ad = make_store_ad(items=(StoreItem(plate="А001АА77", price=Price(100_000)),))
    use_case = AddStoreItemsUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    with pytest.raises(StoreItemsAlreadyExistException):
        await use_case(
            AddStoreItemsRequest(
                ad_id=1, items=[StoreItem(plate="А001АА77", price=Price(999))]
            )
        )


async def test_add_store_items_raises_for_non_store_ad():
    sale_ad = Ad(
        id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.READY
    )
    use_case = AddStoreItemsUseCase(
        ad_repo=FakeAdRepo([sale_ad]), transaction_manager=FakeTransactionManager()
    )

    with pytest.raises(AdNotFoundException):
        await use_case(
            AddStoreItemsRequest(
                ad_id=1, items=[StoreItem(plate="А001АА77", price=Price(100))]
            )
        )


# ---------- DeleteStoreItemUseCase ----------


async def test_delete_store_item_removes_matching_plate():
    ad = make_store_ad(
        items=(
            StoreItem(plate="А001АА77", price=Price(100_000)),
            StoreItem(plate="В002ВВ77", price=Price(200_000)),
        )
    )
    use_case = DeleteStoreItemUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    dto = await use_case(DeleteStoreItemRequest(ad_id=1, plate="А001АА77"))

    remaining_plates = {i.plate for i in dto.store_content.items}
    assert remaining_plates == {"В002ВВ77"}


async def test_delete_store_item_raises_for_missing_ad():
    use_case = DeleteStoreItemUseCase(
        ad_repo=FakeAdRepo([]), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(AdNotFoundException):
        await use_case(DeleteStoreItemRequest(ad_id=1, plate="А001АА77"))


# ---------- GetUserStoreUseCase ----------


async def test_get_user_store_returns_dto():
    ad = make_store_ad()
    use_case = GetUserStoreUseCase(ad_repo=FakeAdRepo([ad]))
    dto = await use_case(GetUserStoreRequest(user_id=1, region_id=1))
    assert dto.id == 1


async def test_get_user_store_raises_when_not_found():
    use_case = GetUserStoreUseCase(ad_repo=FakeAdRepo([]))
    with pytest.raises(AdNotFoundException):
        await use_case(GetUserStoreRequest(user_id=1, region_id=1))


# ---------- UpdateStoreItemUseCase ----------


async def test_update_store_item_changes_price_and_plate():
    ad = make_store_ad(items=(StoreItem(plate="А001АА77", price=Price(100_000)),))
    use_case = UpdateStoreItemUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    dto = await use_case(
        UpdateStoreItemRequest(
            ad_id=1, plate="А001АА77", new_plate="В002ВВ77", new_price=250_000
        )
    )

    item = dto.store_content.items[0]
    assert item.plate == "В002ВВ77"
    assert item.price.value == 250_000


async def test_update_store_item_leaves_other_items_untouched():
    ad = make_store_ad(
        items=(
            StoreItem(plate="А001АА77", price=Price(100_000)),
            StoreItem(plate="В002ВВ77", price=Price(200_000)),
        )
    )
    use_case = UpdateStoreItemUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    dto = await use_case(
        UpdateStoreItemRequest(ad_id=1, plate="А001АА77", new_price=999)
    )

    untouched = next(i for i in dto.store_content.items if i.plate == "В002ВВ77")
    assert untouched.price.value == 200_000


async def test_update_store_item_raises_for_missing_ad():
    use_case = UpdateStoreItemUseCase(
        ad_repo=FakeAdRepo([]), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(AdNotFoundException):
        await use_case(UpdateStoreItemRequest(ad_id=1, plate="X"))


# ---------- UpdateStoreUseCase ----------


async def test_update_store_updates_only_provided_fields():
    ad = make_store_ad()
    use_case = UpdateStoreUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    dto = await use_case(UpdateStoreRequest(ad_id=1, shop_name="New Shop Name"))

    assert dto.store_content.shop_name == "New Shop Name"
    assert dto.store_content.city == "City"  # unchanged


async def test_update_store_raises_for_missing_ad():
    use_case = UpdateStoreUseCase(
        ad_repo=FakeAdRepo([]), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(AdNotFoundException):
        await use_case(UpdateStoreRequest(ad_id=1, shop_name="X"))
