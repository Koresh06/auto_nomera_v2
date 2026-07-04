from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from src.application.dtos.publication_stats import (
    AdTypeStatDTO,
    PublicationStatsDTO,
    StatusStatDTO,
)
from src.domain.entities.publication import Publication
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.exceptions.publication import PublicationNotFoundException
from src.domain.enums.ad import AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceStatus
from src.infrastructure.database.models import PublicationModel
from src.infrastructure.database.models.ad import AdModel
from src.infrastructure.database.models.publication_service import (
    PublicationServiceModel,
)
from src.infrastructure.database.models.region import RegionModel
from src.infrastructure.database.models.user import UserModel


class SQLAlchemyPublicationRepo(PublicationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, publication_id: int) -> Publication | None:
        query = select(PublicationModel).where(PublicationModel.id == publication_id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def create(self, publication: Publication) -> Publication:
        model = PublicationModel.from_entity(publication)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()

    async def save(self, publication: Publication) -> None:
        query = select(PublicationModel).where(PublicationModel.id == publication.id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            raise PublicationNotFoundException(publication.id)
        PublicationModel._update_model(model, publication)
        await self._session.flush()

    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]:
        query = select(PublicationModel).where(PublicationModel.ad_id == ad_id)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [m.to_entity() for m in models]

    async def list_by_user(
        self,
        user_id: int,
        region_id: int,
    ) -> list[tuple[Publication, str | None, str | None]]:
        query = (
            select(PublicationModel, AdModel.plate_number, AdModel.shop_name)
            .join(AdModel, PublicationModel.ad_id == AdModel.id)
            .where(
                AdModel.user_id == user_id,
                AdModel.region_id == region_id,
                PublicationModel.is_child.is_(False),
                PublicationModel.status.notin_(
                    [
                        PublicationStatus.CANCELED,
                        PublicationStatus.REPLACED,
                    ]
                ),
            )
            .options(selectinload(PublicationModel.services))
            .order_by(PublicationModel.created_at.desc())
        )
        result = await self._session.execute(query)
        return [
            (pub_model.to_entity(), plate, shop_name)
            for pub_model, plate, shop_name in result.all()
        ]

    async def count_scheduled_by_user(
        self,
        user_id: int,
        region_id: int,
        ad_type: AdType,
        from_utc: datetime,
    ) -> int:
        query = (
            select(func.count(PublicationModel.id))
            .join(AdModel, PublicationModel.ad_id == AdModel.id)
            .where(
                AdModel.user_id == user_id,
                AdModel.region_id == region_id,
                AdModel.ad_type == ad_type,
                PublicationModel.status.in_(
                    [
                        PublicationStatus.SCHEDULED,
                        PublicationStatus.PUBLISHED,
                        PublicationStatus.PUBLISHING,
                    ]
                ),
                PublicationModel.publish_at_utc >= from_utc,
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one() or 0

    async def find_last_by_plate(
        self,
        user_id: int,
        region_id: int,
        plate: str,
        from_utc: datetime,
    ) -> Publication | None:
        query = (
            select(PublicationModel)
            .join(AdModel, PublicationModel.ad_id == AdModel.id)
            .where(
                AdModel.user_id == user_id,
                AdModel.region_id == region_id,
                AdModel.plate_number == plate,
                PublicationModel.status.in_(
                    [
                        PublicationStatus.SCHEDULED,
                        PublicationStatus.PUBLISHED,
                        PublicationStatus.PUBLISHING,
                    ]
                ),
                PublicationModel.publish_at_utc >= from_utc,
            )
            .order_by(PublicationModel.publish_at_utc.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def list_pre_publication(
        self,
        region_id: int,
        now_utc: datetime,
        before_utc: datetime,
    ) -> list[Publication]:
        query = (
            select(PublicationModel)
            .where(
                PublicationModel.region_id == region_id,
                PublicationModel.status == PublicationStatus.SCHEDULED,
                PublicationModel.publish_at_utc >= now_utc,
                PublicationModel.publish_at_utc <= before_utc,
                PublicationModel.is_child.is_(False),
            )
            .order_by(PublicationModel.publish_at_utc.asc())
        )
        result = await self._session.execute(query)
        return [m.to_entity() for m in result.scalars().all()]

    async def get_stats(
        self,
        *,
        since_utc: datetime | None = None,
        region_id: int | None = None,
    ) -> PublicationStatsDTO:
        conds = []
        if since_utc is not None:
            conds.append(PublicationModel.publish_at_utc >= since_utc)
        if region_id is not None:
            conds.append(PublicationModel.region_id == region_id)

        where = and_(*conds) if conds else True

        # разбивка по статусам
        status_rows = (
            await self._session.execute(
                select(
                    PublicationModel.status,
                    func.count().label("cnt"),
                )
                .where(where)
                .group_by(PublicationModel.status)
            )
        ).all()

        by_status = [StatusStatDTO(status=r.status, count=r.cnt) for r in status_rows]
        total = sum(s.count for s in by_status)

        # разбивка по типу объявления (join на ads)
        type_rows = (
            await self._session.execute(
                select(
                    AdModel.ad_type,
                    func.count().label("cnt"),
                )
                .select_from(PublicationModel)  # ← явный левый борт
                .join(AdModel, PublicationModel.ad_id == AdModel.id)
                .where(where)
                .group_by(AdModel.ad_type)
            )
        ).all()

        by_ad_type = [AdTypeStatDTO(ad_type=r.ad_type, count=r.cnt) for r in type_rows]

        # топ-регион (только без фильтра по региону)
        top_region_title = None
        top_region_count = 0
        if region_id is None:
            region_conds = []
            if since_utc is not None:
                region_conds.append(PublicationModel.publish_at_utc >= since_utc)
            region_where = and_(*region_conds) if region_conds else True

            top = (
                await self._session.execute(
                    select(
                        RegionModel.title,
                        func.count(PublicationModel.id).label("cnt"),
                    )
                    .select_from(PublicationModel)
                    .join(RegionModel, PublicationModel.region_id == RegionModel.id)
                    .where(region_where)
                    .group_by(RegionModel.title)
                    .order_by(func.count(PublicationModel.id).desc())
                    .limit(1)
                )
            ).first()
            if top:
                top_region_title = top.title
                top_region_count = top.cnt

        urgent_conds = [AdModel.ad_type == AdType.URGENT_BUYOUT]
        if since_utc is not None:
            urgent_conds.append(AdModel.created_at >= since_utc)
        if region_id is not None:
            urgent_conds.append(AdModel.region_id == region_id)

        urgent_count = (
            await self._session.execute(
                select(func.count()).select_from(AdModel).where(and_(*urgent_conds))
            )
        ).scalar() or 0

        if urgent_count > 0:
            by_ad_type.append(
                AdTypeStatDTO(ad_type=AdType.URGENT_BUYOUT, count=urgent_count)
            )

        return PublicationStatsDTO(
            total=total,
            by_status=by_status,
            by_ad_type=by_ad_type,
            top_region_title=top_region_title,
            top_region_count=top_region_count,
        )

    async def list_scheduled_by_region(
        self,
        region_id: int,
        from_utc: datetime,
        to_utc: datetime,
    ) -> list[tuple[Publication, str | None, str | None, str | None, int | None]]:
        rows = (
            await self._session.execute(
                select(
                    PublicationModel,
                    AdModel.plate_number,
                    AdModel.ad_type,
                    AdModel.username,
                    UserModel.tg_id,
                )
                .select_from(PublicationModel)
                .join(AdModel, PublicationModel.ad_id == AdModel.id)
                .join(UserModel, AdModel.user_id == UserModel.id)
                .where(
                    PublicationModel.region_id == region_id,
                    PublicationModel.publish_at_utc >= from_utc,
                    PublicationModel.publish_at_utc < to_utc,
                    PublicationModel.is_child.is_(False),
                    PublicationModel.status.in_(
                        [
                            PublicationStatus.SCHEDULED,
                            PublicationStatus.PUBLISHED,
                            PublicationStatus.PUBLISHING,
                        ]
                    ),
                )
                .order_by(PublicationModel.publish_at_utc)
            )
        ).all()

        return [
            (
                r.PublicationModel.to_entity(),
                r.plate_number,
                r.ad_type,
                r.username,
                r.tg_id,
            )
            for r in rows
        ]

    async def list_scheduled_for_catalog(self, region_id: int):
        rows = (
            await self._session.execute(
                select(PublicationModel, AdModel, UserModel.tg_id)
                .select_from(PublicationModel)
                .join(AdModel, PublicationModel.ad_id == AdModel.id)
                .join(UserModel, AdModel.user_id == UserModel.id)
                .where(
                    PublicationModel.region_id == region_id,
                    PublicationModel.status == PublicationStatus.SCHEDULED,
                    PublicationModel.is_child.is_(False),
                    AdModel.ad_type != AdType.URGENT_BUYOUT,
                )
                .options(selectinload(PublicationModel.services))
                .order_by(PublicationModel.publish_at_utc)
            )
        ).all()
        return [
            (r.PublicationModel.to_entity(), r.AdModel.to_entity(), r.tg_id)
            for r in rows
        ]

    async def count_scheduled(self, region_id: int | None = None) -> int:
        q = select(func.count(PublicationModel.id)).where(
            PublicationModel.status == PublicationStatus.SCHEDULED,
            PublicationModel.is_child.is_(False),
        )
        if region_id is not None:
            q = q.where(PublicationModel.region_id == region_id)
        return (await self._session.execute(q)).scalar() or 0

    async def count_services(
        self, since_utc: datetime | None = None, region_id: int | None = None
    ):
        conds = [
            PublicationServiceModel.status.in_(
                [
                    PublicationServiceStatus.ACTIVE,
                    PublicationServiceStatus.USED,
                ]
            )
        ]
        if since_utc is not None:
            conds.append(PublicationServiceModel.created_at >= since_utc)
        if region_id is not None:
            conds.append(PublicationModel.region_id == region_id)

        q = (
            select(PublicationServiceModel.type, func.count().label("cnt"))
            .select_from(PublicationServiceModel)
            .join(
                PublicationModel,
                PublicationServiceModel.publication_id == PublicationModel.id,
            )
            .where(and_(*conds))
            .group_by(PublicationServiceModel.type)
        )
        rows = (await self._session.execute(q)).all()
        by_type = [(r.type, r.cnt) for r in rows]
        total = sum(c for _, c in by_type)
        return total, by_type
