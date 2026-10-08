"""
Regression test for AUD-08: PublishPublicationUseCase used to commit the
PUBLISHING transition only once, at the very end of the method — after the
Telegram API call. If the worker crashed (or the stream message was
redelivered, or two workers raced on the same task) between the Telegram
send and that final commit, the DB would roll back to SCHEDULED while the
post had already gone out, and a retry/redelivery would publish it again.

The fix commits mark_publishing() immediately, before any Telegram call, so
a second concurrent/redelivered attempt sees the already-committed
PUBLISHING status and fails fast at mark_publishing()'s own domain guard
(status must be SCHEDULED) instead of silently sending a second post.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
    PublishPublicationUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.entities.user import User
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.role import UserRole
from src.domain.exceptions.publication import InvalidPublicationState
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.store_content import StoreContent
from src.domain.value_objects.timezone_name import TimezoneName


class FakePublicationRepo:
    def __init__(self, pub: Publication) -> None:
        self._store: dict[int, Publication] = {pub.id: pub}

    async def get_by_id(self, publication_id: int) -> Publication | None:
        return self._store.get(publication_id)

    async def save(self, publication: Publication) -> None:
        self._store[publication.id] = publication


class FakeAdRepo:
    def __init__(self, ad: Ad) -> None:
        self._ad = ad

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._ad if self._ad.id == ad_id else None


class FakeRegionRepo:
    def __init__(self, region: Region) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        return self._region if self._region.id == region_id else None


class FakeUserRepo:
    def __init__(self, user: User) -> None:
        self._user = user

    async def get_by_id(self, user_id: int) -> User | None:
        return self._user if self._user.id == user_id else None


class FakeTelegramPublisher:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def publish_text(self, *, channel_id: int, text: str):
        from src.application.ports.telegram.telegram_publisher import PublishResult

        self._events.append("telegram_publish")
        return PublishResult(channel_id=channel_id, message_id=999)

    async def publish_photo(self, *, channel_id: int, image_file_id: str, caption: str):
        from src.application.ports.telegram.telegram_publisher import PublishResult

        self._events.append("telegram_publish")
        return PublishResult(channel_id=channel_id, message_id=999)


class FakeTransactionManager:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def commit(self) -> None:
        self._events.append("commit")

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass


def build_use_case(
    events: list[str], pub_repo: FakePublicationRepo, ad: Ad, region: Region, user: User
):
    return PublishPublicationUseCase(
        publication_repo=pub_repo,
        ad_repo=FakeAdRepo(ad),
        region_repo=FakeRegionRepo(region),
        user_repo=FakeUserRepo(user),
        telegram=FakeTelegramPublisher(events),
        image_processor=None,  # not used for STORE / no HIGHLIGHT service
        renderer=AdTextRenderer(
            bot_url="https://t.me/bot", buyout_url="https://t.me/buyout"
        ),
        scheduler=None,  # not used: no PIN/AUTOPUBLISH/PRIORITY_PUBLISH services attached
        task_queue=None,
        settings=MagicMock(app=MagicMock(pre_publication_window_hours=2)),
        time_resolver=PublishTimeResolver(),
        transaction_manager=FakeTransactionManager(events),
    )


def make_store_ad() -> Ad:
    ad = Ad(id=1, user_id=1, region_id=1, ad_type=AdType.STORE, status=AdStatus.READY)
    ad.fill_store_content(
        StoreContent(
            shop_name="Shop",
            city="City",
            contacts=Contacts(username="shop"),
            items=(),
        )
    )
    return ad


def make_region() -> Region:
    return Region(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )


def make_user() -> User:
    return User(id=1, tg_id=1, role=UserRole.USER, phone=None, region_id=1, balance=0)


async def test_publishing_status_is_committed_before_telegram_call():
    """The commit marking PUBLISHING must happen BEFORE the Telegram API
    call, not after."""
    events: list[str] = []
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    pub_repo = FakePublicationRepo(pub)
    use_case = build_use_case(
        events, pub_repo, make_store_ad(), make_region(), make_user()
    )

    await use_case(
        PublishPublicationRequest(publication_id=1, now_utc=datetime.now(timezone.utc))
    )

    assert "commit" in events
    assert "telegram_publish" in events
    first_commit_index = events.index("commit")
    telegram_index = events.index("telegram_publish")
    assert first_commit_index < telegram_index, (
        f"commit must happen before the Telegram call, got order: {events}"
    )


async def test_redelivery_while_already_publishing_raises_instead_of_reposting():
    """AUD-08's actual protection: once a publication is (committed) in
    PUBLISHING, a second invocation for the same publication_id must not
    silently publish a second time — it must fail at the domain guard."""
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.PUBLISHING)
    pub_repo = FakePublicationRepo(pub)
    events: list[str] = []
    use_case = build_use_case(
        events, pub_repo, make_store_ad(), make_region(), make_user()
    )

    with pytest.raises(InvalidPublicationState):
        await use_case(
            PublishPublicationRequest(
                publication_id=1, now_utc=datetime.now(timezone.utc)
            )
        )

    assert "telegram_publish" not in events
