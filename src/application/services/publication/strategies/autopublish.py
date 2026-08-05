from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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
        if service.params is None:
            service.mark_used()
            return
        days = service.params.get("days", 7)
        if publication.slot is not None:
            base_day = publication.slot.local_day
            base_time = publication.slot.local_time
        else:
            local_dt = (
                publication.published_at_utc or datetime.now(timezone.utc)
            ).astimezone(ZoneInfo(context.region.timezone.value))
            base_day = local_dt.date()
            base_time = local_dt.time()
        for i in range(1, days):
            next_slot = SlotKey(
                region_id=publication.region_id,
                local_day=base_day + timedelta(days=i),
                local_time=base_time,
            )
            publish_at_utc = context.time_resolver.resolve_publish_at_utc(
                tz=context.region.timezone,
                slot=next_slot,
            )
            new_pub = Publication(
                ad_id=publication.ad_id,
                region_id=publication.region_id,
                is_child=True,
            )
            new_pub.schedule(slot=next_slot, publish_at_utc=publish_at_utc)
            created = await context.publication_repo.create(new_pub)
            await context.scheduler.schedule_publication(
                publication_id=created.id,
                run_at_utc=publish_at_utc,
            )

            notify_at = publish_at_utc - timedelta(
                hours=context.pre_publication_window_hours
            )
            if notify_at > datetime.now(timezone.utc):
                await context.task_queue.schedule(
                    task_name="notify_pre_publication_users",
                    args=(publication.ad_id,),
                    run_at_utc=notify_at,
                )
                created.notify_scheduled = True
                await context.publication_repo.save(created)

        service.mark_used()
