from datetime import UTC, datetime, timedelta

from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.application.services.publication.context import ServiceContext
from src.domain.value_objects.slot_key import SlotKey


class AutopublishStrategy:
    async def apply(
        self,
        publication: Publication,
        service: PublicationService,
        context: ServiceContext,
    ) -> None:
        if publication.slot is None:
            service.mark_used()
            return

        if service.params is None:
            service.mark_used()
            return
        
        days = service.params.get("days", 7)
        for i in range(1, days):
            next_slot = SlotKey(
                region_id=publication.region_id,
                local_day=publication.slot.local_day + timedelta(days=i),
                local_time=publication.slot.local_time,
            )
            publish_at_utc = context.time_resolver.resolve_publish_at_utc(
                tz=context.region.timezone,
                slot=next_slot,
            )
            # now_utc = datetime.now(UTC)
            # publish_at_utc = now_utc + timedelta(seconds=30 * i) # test
            new_pub = Publication(
                ad_id=publication.ad_id,
                region_id=publication.region_id,
            )
            new_pub.schedule(slot=next_slot, publish_at_utc=publish_at_utc)
            created = await context.publication_repo.create(new_pub)
            await context.scheduler.schedule_publication(
                publication_id=created.id,
                run_at_utc=publish_at_utc,
            )

        service.mark_used()
