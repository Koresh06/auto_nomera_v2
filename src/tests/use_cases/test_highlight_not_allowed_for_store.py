"""
Regression test for AUD-19: HIGHLIGHT is meaningless for STORE ads (no single
ad image — a store lists several priced items instead), and that was only
enforced in publish_publication.py and in the UI's service list filtering.
Any other application-layer entry point could charge a user for HIGHLIGHT on
a STORE ad with zero effect. ensure_service_allowed_for_ad_type() is now
checked in BuyPublicationServiceUseCase (balance path, before charging) and
ApplyServiceToPublishedUseCase (apply-to-published path).
"""

from decimal import Decimal

import pytest

from src.application.use_cases.publication_service.apply_service import (
    ApplyServiceToPublishedRequest,
    ApplyServiceToPublishedUseCase,
)
from src.application.use_cases.publication_service.buy_publication_service import (
    BuyPublicationServiceRequest,
    BuyPublicationServiceUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.entities.user import User
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.enums.role import UserRole
from src.domain.exceptions.publication import ServiceNotAllowed
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.store_content import StoreContent


class FakeUserRepo:
    def __init__(self, user: User) -> None:
        self._user = user
        self.saved: list[User] = []

    async def get_by_id(self, user_id: int) -> User | None:
        return self._user if self._user.id == user_id else None

    async def save(self, user: User) -> None:
        self.saved.append(user)


class FakePublicationRepo:
    def __init__(self, pub: Publication) -> None:
        self._pub = pub
        self.saved: list[Publication] = []

    async def get_by_id(self, publication_id: int) -> Publication | None:
        return self._pub if self._pub.id == publication_id else None

    async def save(self, publication: Publication) -> None:
        self.saved.append(publication)


class FakeAdRepo:
    def __init__(self, ad: Ad) -> None:
        self._ad = ad

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._ad if self._ad.id == ad_id else None


class FakeServiceDefRepo:
    def __init__(self, definition: ServiceDefinition) -> None:
        self._definition = definition

    async def get_by_type(self, service_type) -> ServiceDefinition:
        return self._definition


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


def make_store_ad() -> Ad:
    ad = Ad(id=1, user_id=1, region_id=1, ad_type=AdType.STORE, status=AdStatus.READY)
    ad.fill_store_content(
        StoreContent(shop_name="Shop", city="City", contacts=Contacts(), items=())
    )
    return ad


async def test_buy_publication_service_rejects_highlight_for_store_without_charging():
    user = User(
        id=1,
        tg_id=1,
        role=UserRole.USER,
        phone=None,
        region_id=1,
        balance=Decimal("1000"),
    )
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    definition = ServiceDefinition(
        id=1, title="Highlight", type=PublicationServiceType.HIGHLIGHT, price=100
    )

    use_case = BuyPublicationServiceUseCase(
        user_repo=FakeUserRepo(user),
        publication_repo=FakePublicationRepo(pub),
        ad_repo=FakeAdRepo(make_store_ad()),
        service_def_repo=FakeServiceDefRepo(definition),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ServiceNotAllowed):
        await use_case(
            BuyPublicationServiceRequest(
                publication_id=1,
                service_type=PublicationServiceType.HIGHLIGHT,
                user_id=1,
            )
        )

    # money must NOT have been charged
    assert user.balance == Decimal("1000")
    assert len(pub.services) == 0


async def test_buy_publication_service_allows_highlight_for_sale_ad():
    user = User(
        id=1,
        tg_id=1,
        role=UserRole.USER,
        phone=None,
        region_id=1,
        balance=Decimal("1000"),
    )
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    sale_ad = Ad(
        id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.READY
    )
    definition = ServiceDefinition(
        id=1, title="Highlight", type=PublicationServiceType.HIGHLIGHT, price=100
    )

    use_case = BuyPublicationServiceUseCase(
        user_repo=FakeUserRepo(user),
        publication_repo=FakePublicationRepo(pub),
        ad_repo=FakeAdRepo(sale_ad),
        service_def_repo=FakeServiceDefRepo(definition),
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(
        BuyPublicationServiceRequest(
            publication_id=1, service_type=PublicationServiceType.HIGHLIGHT, user_id=1
        )
    )

    assert user.balance == Decimal("900")
    assert len(pub.services) == 1


async def test_apply_service_to_published_rejects_highlight_for_store():
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.PUBLISHED)
    pub.services.append(
        PublicationService(
            id=1,
            type=PublicationServiceType.HIGHLIGHT,
            status=PublicationServiceStatus.ACTIVE,
        )
    )

    use_case = ApplyServiceToPublishedUseCase(
        publication_repo=FakePublicationRepo(pub),
        ad_repo=FakeAdRepo(make_store_ad()),
        region_repo=None,
        user_repo=None,
        telegram=None,
        image_processor=None,
        renderer=None,
        scheduler=None,
        task_queue=None,
        settings=None,
        time_resolver=None,
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ServiceNotAllowed):
        await use_case(
            ApplyServiceToPublishedRequest(
                publication_id=1, service_type=PublicationServiceType.HIGHLIGHT
            )
        )
