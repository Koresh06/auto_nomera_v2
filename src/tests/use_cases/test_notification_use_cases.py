"""
Coverage for src/application/use_cases/notification/* — NotifyAdminsAboutUrgentUseCase
and NotifyPrePublicationUsersUseCase — previously entirely untested.
"""

from unittest.mock import MagicMock

import pytest

from src.application.exceptions.ad import AdNotFoundException
from src.application.exceptions.region import RegionNotFoundException
from src.application.use_cases.notification.notify_admins_urgent import (
    NotifyAdminsAboutUrgentRequest,
    NotifyAdminsAboutUrgentUseCase,
)
from src.application.use_cases.notification.notify_pre_publication_users import (
    NotifyPrePublicationUsersRequest,
    NotifyPrePublicationUsersUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.region import Region
from src.domain.entities.user import User
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.role import UserRole
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName


class FakeAdRepo:
    def __init__(self, ads: list[Ad] | None = None) -> None:
        self._store = {a.id: a for a in (ads or [])}

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._store.get(ad_id)


class FakeRegionRepo:
    def __init__(self, region: Region | None) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None


class FakeUserRepo:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users = users or []

    async def find_with_active_pre_publication(self, region_id: int) -> list[User]:
        return self._users


class FakeNotificationService:
    def __init__(self) -> None:
        self.admin_calls: list[dict] = []
        self.user_calls: list[dict] = []

    async def notify_admins(
        self, *, text: str, photo_id=None, reply_markup=None
    ) -> None:
        self.admin_calls.append(
            {"text": text, "photo_id": photo_id, "reply_markup": reply_markup}
        )

    async def notify_users(
        self,
        *,
        user_ids: list[int],
        text: str,
        photo_id=None,
        reply_markup=None,
        throttle_seconds: float = 0.05,
    ) -> None:
        self.user_calls.append(
            {
                "user_ids": user_ids,
                "text": text,
                "photo_id": photo_id,
                "reply_markup": reply_markup,
            }
        )


def make_ad(**overrides) -> Ad:
    defaults = dict(
        id=1,
        user_id=1,
        region_id=1,
        ad_type=AdType.URGENT_BUYOUT,
        status=AdStatus.PUBLISHED,
    )
    defaults.update(overrides)
    ad = Ad(**defaults)
    if ad.content is None:
        ad.fill_content(
            AdContent(
                plate_number="А001АА77",
                city="City",
                price=Price(100_000),
                contacts=Contacts(username="seller"),
                image_file_id="photo-1",
            )
        )
    return ad


def make_region(**overrides) -> Region:
    defaults = dict(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )
    defaults.update(overrides)
    return Region(**defaults)


def make_user(**overrides) -> User:
    defaults = dict(
        id=1, tg_id=1001, role=UserRole.USER, phone=None, region_id=1, balance=0
    )
    defaults.update(overrides)
    return User(**defaults)


def make_settings() -> MagicMock:
    settings = MagicMock()
    settings.telegram.bot_url = "https://t.me/test_bot"
    settings.telegram.buyout_url = "https://t.me/test_bot?start=buyout"
    return settings


# ---------- NotifyAdminsAboutUrgentUseCase ----------


async def test_notify_admins_urgent_raises_when_ad_missing():
    use_case = NotifyAdminsAboutUrgentUseCase(
        ad_repo=FakeAdRepo([]), notification_service=FakeNotificationService()
    )

    with pytest.raises(AdNotFoundException):
        await use_case(NotifyAdminsAboutUrgentRequest(ad_id=1))


async def test_notify_admins_urgent_sends_text_with_ad_details():
    ad = make_ad(id=1)
    notification_service = FakeNotificationService()
    use_case = NotifyAdminsAboutUrgentUseCase(
        ad_repo=FakeAdRepo([ad]), notification_service=notification_service
    )
    markup = object()

    await use_case(NotifyAdminsAboutUrgentRequest(ad_id=1, reply_markup=markup))

    assert len(notification_service.admin_calls) == 1
    call = notification_service.admin_calls[0]
    assert "СРОЧНЫЙ ВЫКУП" in call["text"]
    assert "А001АА77" in call["text"]
    assert call["photo_id"] == "photo-1"
    assert call["reply_markup"] is markup


# ---------- NotifyPrePublicationUsersUseCase ----------


async def test_notify_pre_publication_users_raises_when_ad_missing():
    use_case = NotifyPrePublicationUsersUseCase(
        ad_repo=FakeAdRepo([]),
        region_repo=FakeRegionRepo(None),
        user_repo=FakeUserRepo([]),
        notification_service=FakeNotificationService(),
        settings=make_settings(),
    )

    with pytest.raises(AdNotFoundException):
        await use_case(NotifyPrePublicationUsersRequest(ad_id=1))


async def test_notify_pre_publication_users_raises_when_region_missing():
    ad = make_ad(id=1, region_id=1)
    use_case = NotifyPrePublicationUsersUseCase(
        ad_repo=FakeAdRepo([ad]),
        region_repo=FakeRegionRepo(None),
        user_repo=FakeUserRepo([]),
        notification_service=FakeNotificationService(),
        settings=make_settings(),
    )

    with pytest.raises(RegionNotFoundException):
        await use_case(NotifyPrePublicationUsersRequest(ad_id=1))


async def test_notify_pre_publication_users_skips_when_no_active_users():
    ad = make_ad(id=1, region_id=1)
    region = make_region(id=1)
    notification_service = FakeNotificationService()
    use_case = NotifyPrePublicationUsersUseCase(
        ad_repo=FakeAdRepo([ad]),
        region_repo=FakeRegionRepo(region),
        user_repo=FakeUserRepo([]),
        notification_service=notification_service,
        settings=make_settings(),
    )

    await use_case(NotifyPrePublicationUsersRequest(ad_id=1))

    assert notification_service.user_calls == []


async def test_notify_pre_publication_users_notifies_active_users():
    ad = make_ad(id=1, region_id=1, ad_type=AdType.SALE)
    region = make_region(id=1)
    users = [make_user(id=1, tg_id=111), make_user(id=2, tg_id=222)]
    notification_service = FakeNotificationService()
    use_case = NotifyPrePublicationUsersUseCase(
        ad_repo=FakeAdRepo([ad]),
        region_repo=FakeRegionRepo(region),
        user_repo=FakeUserRepo(users),
        notification_service=notification_service,
        settings=make_settings(),
    )

    await use_case(NotifyPrePublicationUsersRequest(ad_id=1))

    assert len(notification_service.user_calls) == 1
    call = notification_service.user_calls[0]
    assert call["user_ids"] == [111, 222]
    assert "раннему доступу" in call["text"]
    assert "А001АА77" in call["text"]
    assert call["photo_id"] == "photo-1"
    assert call["reply_markup"] is not None
