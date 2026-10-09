"""Создание реальных строк в тестовой БД через настоящие репозитории."""

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.ad import Ad
from src.domain.entities.payment import Payment
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.entities.user import User
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.domain.enums.publication import PublicationStatus
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.slot_key import SlotKey
from src.domain.value_objects.store_content import StoreContent, StoreItem
from src.domain.value_objects.timezone_name import TimezoneName
from src.infrastructure.repositories.ad.sqlalchemy import SQLAlchemyAdRepo
from src.infrastructure.repositories.payment.sqlalchemy import SQLAlchemyPaymentRepo
from src.infrastructure.repositories.publication.sqlalchemy import (
    SQLAlchemyPublicationRepo,
)
from src.infrastructure.repositories.region.sqlalchemy import (
    SQLAlchemyRegionRepository,
)
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo


async def make_region(
    session: AsyncSession,
    *,
    title: str = "Москва",
    tz: str = "Europe/Moscow",
    channel_id: int = -1001,
    settings: RegionSettings | None = None,
) -> Region:
    region = Region(
        title=title,
        timezone=TimezoneName(tz),
        channel_id=channel_id,
        channel_username="chan",
        metadata=RegionMetadata(tg_group_url="https://t.me/g"),
        settings=settings or RegionSettings(),
    )
    return await SQLAlchemyRegionRepository(session).create(region)


_next_tg = [1000]


async def make_user(
    session: AsyncSession,
    region_id: int,
    *,
    tg_id: int | None = None,
    balance: Decimal = Decimal("0"),
    **kw,
) -> User:
    if tg_id is None:
        _next_tg[0] += 1
        tg_id = _next_tg[0]
    user = User(
        tg_id=tg_id,
        region_id=region_id,
        phone=kw.pop("phone", None),
        balance=balance,
        **kw,
    )
    return await SQLAlchemyUserRepo(session).add(user)


def ad_content(plate: str = "А123ВС77", price: int = 100_000) -> AdContent:
    return AdContent(
        plate_number=plate,
        city="Москва",
        price=Price(price),
        contacts=Contacts(username="seller", phone="+79990000000"),
        caption="cap",
        image_file_id="file-1",
    )


async def make_ad(
    session: AsyncSession,
    user: User,
    *,
    ad_type: AdType = AdType.SALE,
    status: AdStatus = AdStatus.READY,
    plate: str = "А123ВС77",
    region_id: int | None = None,
) -> Ad:
    ad = Ad(
        user_id=user.id,
        region_id=region_id or user.region_id,
        ad_type=ad_type,
        status=status,
    )
    if ad_type == AdType.STORE:
        ad.fill_store_content(
            StoreContent(
                shop_name="Shop",
                city="Москва",
                contacts=Contacts(username="shop"),
                items=(StoreItem(plate=plate, price=Price(500)),),
            )
        )
    else:
        ad.fill_content(ad_content(plate))
    return await SQLAlchemyAdRepo(session).create(ad)


def slot(region_id: int, day: date, hh: int = 10) -> SlotKey:
    return SlotKey(region_id=region_id, local_day=day, local_time=time(hh, 0))


async def make_publication(
    session: AsyncSession,
    ad: Ad,
    *,
    status: PublicationStatus = PublicationStatus.SCHEDULED,
    publish_at_utc: datetime | None = None,
    slot_key: SlotKey | None = None,
    is_child: bool = False,
    services: list | None = None,
) -> Publication:
    pub = Publication(
        ad_id=ad.id,
        region_id=ad.region_id,
        status=status,
        slot=slot_key,
        publish_at_utc=publish_at_utc or datetime.now(timezone.utc),
        is_child=is_child,
        services=services or [],
    )
    return await SQLAlchemyPublicationRepo(session).create(pub)


async def make_payment(
    session: AsyncSession,
    user: User,
    *,
    external_id: str,
    amount: Decimal = Decimal("100"),
    method: PaymentMethod = PaymentMethod.YOOKASSA,
    status: PaymentStatus = PaymentStatus.PAID,
    purpose: PaymentPurpose = PaymentPurpose.BALANCE_TOPUP,
    meta: dict | None = None,
    paid_at: datetime | None = None,
) -> Payment:
    payment = Payment(
        external_id=external_id,
        user_id=user.id,
        method=method,
        amount=amount,
        status=status,
        purpose=purpose,
        meta=meta or {},
        paid_at=paid_at
        or (datetime.now(timezone.utc) if status == PaymentStatus.PAID else None),
    )
    return await SQLAlchemyPaymentRepo(session).create(payment)
